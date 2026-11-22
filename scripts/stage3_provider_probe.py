"""Bounded, authenticated organizer DEV probe. No dataset, tokens, transcripts, audio or URLs with dataset codes are logged."""
import asyncio
import json
import os
import sys
import time
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path

import httpx

from backend.clients import HackClient, ModelClient
from backend.core import validate_schema
from backend.runner import Solution
from scripts.check_dev import compare, missing_records
from scripts.sleep_audit import audit

OUT = Path("stage3-live-evidence.json")
RESULT = {
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "sha": os.environ.get("SAIN_SOURCE_SHA", "unknown"),
    "provider": "SAIN hack-api / Bifrost",
    "scope": "authorized dev only; no closed online/final assessment",
    "checks": {},
}
def mark(name, status, **meta):
    RESULT["checks"][name] = {"status": status, **meta}
    print(f"{name}: {status}", flush=True)

def write():
    OUT.write_text(json.dumps(RESULT, ensure_ascii=False, indent=2), encoding="utf-8")

async def http_call(http, name, method, url, *, headers=None, json_body=None, data=None, files=None, params=None, timeout=15):
    began = time.monotonic()
    try:
        response = await http.request(method, url, headers=headers, json=json_body, data=data, files=files, params=params, timeout=timeout)
    except httpx.RequestError as e:
        mark(name, "NOT TESTED", transport_error=type(e).__name__, latency_ms=round(1000*(time.monotonic()-began)))
        return None
    mark(name, "PASS" if response.is_success else ("LIMITATION" if response.status_code == 501 else "FAIL"),
         http_status=response.status_code, latency_ms=round(1000*(time.monotonic()-began)), request_type=method,
         endpoint=url.split("?")[0])
    return response

async def official(http):
    base="https://hack-api.be-healthy.tech"
    await http_call(http,"official_health","GET",base+"/health",timeout=8)
    await http_call(http,"official_openapi","GET",base+"/openapi.json",timeout=8)
    token=os.getenv("HACK_TEAM_TOKEN","")
    if not token:
        mark("official_auth","NOT TESTED", reason="HACK_TEAM_TOKEN secret not configured")
        return
    headers={"Authorization":"Bearer "+token}
    response=await http_call(http,"official_dev_getData","GET",base+"/case/2/getData",
                             headers=headers,params={"dataset_code":"case2-dev-v1"},timeout=25)
    if response is None or response.status_code!=200:
        return
    try:
        envelope=response.json()
        data=envelope["dataset"]
        validate_schema("Case2Dataset",data)
        reference=envelope.get("reference")
        n_stays=len(data["stays"]); n_requests=len(data["requests"])
        mark("official_schema","PASS",stays=n_stays,requests=n_requests,reference_available=isinstance(reference,dict))
    except (ValueError,KeyError,TypeError) as e:
        mark("official_schema","FAIL",reason=type(e).__name__)
        return
    # A dev run is a bounded, authorized POST, performed once. No retry of mutating calls.
    model_key=os.getenv("LLM_API_KEY","")
    if not model_key or not os.getenv("LLM_MODEL"):
        mark("official_full_dev_run","NOT TESTED",reason="Model secret/env absent; avoid knowingly incomplete session")
        return
    client=HackClient(token,http)
    try:
        started=time.monotonic()
        run=await client.dev_run()
        rid=run.get("run_id")
        if not isinstance(rid,str) or not rid:
            raise ValueError("run_id absent")
        model=ModelClient(http)
        solution=Solution(data,client,model,rid)
        async with asyncio.timeout(390):
            answer=await solution.run()
        validate_schema("Case2Answers",answer)
        counts={"stays_returned":len(answer["stays"]),"requests_returned":len(answer["requests"]),
                "stays_expected":n_stays,"requests_expected":n_requests,"llm_calls":model.calls,"llm_tokens":model.tokens}
        missing_stays=missing_records(data["stays"],answer["stays"])
        missing_requests=missing_records(data["requests"],answer["requests"])
        mark("official_full_dev_run","PASS" if not missing_stays and not missing_requests else "PARTIAL",
             duration_s=round(time.monotonic()-started,1),**counts,
             missing_stays=len(missing_stays),missing_requests=len(missing_requests))
    except (Exception,TimeoutError) as e:
        mark("official_full_dev_run","FAIL",reason=type(e).__name__)
        return
    if isinstance(reference,dict):
        try:
            ref_requests={r["record_id"]:r for r in reference["requests"]}
            requests={r["record_id"]:r for r in data["requests"]}
            failures=len(missing_requests)
            passed=0
            for item in answer["requests"]:
                request=requests[item["record_id"]]
                expected=ref_requests[item["record_id"]]
                state_resp=await client.request("GET","/room/"+item["session_id"]+"/state",
                                                params={"at":request["at"]},retry=True)
                errors=compare(request["initial_state"],state_resp["state"],expected)
                if [r["response_class"] for r in item["replies"]]!=expected["expected_reply_classes"]:
                    errors.append("reply class")
                if errors: failures+=1
                else: passed+=1
            mark("official_full_state_reference","PASS" if failures==0 else "PARTIAL",
                 requests_passed=passed,requests_total=n_requests,requests_failed=failures)
        except Exception as e:
            mark("official_full_state_reference","PARTIAL",reason=type(e).__name__)
    else:
        mark("official_full_state_reference","NOT TESTED",reason="reference absent")
    # Use raw HTTP here because case 2 validate may legitimately return 501.
    resp=await http_call(http,"official_validate","POST",base+"/case/2/validate",
                        headers={**headers,"Content-Type":"application/json"},json_body=answer,timeout=25)
    if resp is not None and resp.status_code==501:
        mark("official_validate","LIMITATION",http_status=501,reason="case 2 simulator-based validation unsupported")

async def provider(http):
    base="https://bifrost.be-healthy.tech/v1"
    key=os.getenv("LLM_API_KEY","")
    if not key:
        mark("provider_auth","NOT TESTED",reason="LLM_API_KEY secret not configured")
        return
    headers={"Authorization":"Bearer "+key}
    await http_call(http,"provider_models","GET",base+"/models",headers=headers,timeout=15)
    model=os.getenv("LLM_MODEL","gpt-6-luna")
    chat=await http_call(http,"provider_chat","POST",base+"/chat/completions",
                        headers=headers,json_body={"model":model,
                        "messages":[{"role":"system","content":"Верни только JSON с ключом ok и значением true."},
                                    {"role":"user","content":"Проверка соединения."}],
                        "response_format":{"type":"json_object"},"max_tokens":1150},timeout=70)
    if chat is not None and chat.status_code==200:
        try:
            obj=chat.json(); choice=obj["choices"][0]
            payload=json.loads(choice["message"]["content"])
            status="PASS" if payload.get("ok") is True and choice.get("finish_reason")=="stop" else "FAIL"
            mark("provider_chat_result",status,model=model,finish_reason=choice.get("finish_reason"),
                 usage_tokens=obj.get("usage",{}).get("total_tokens"))
        except (ValueError,KeyError,TypeError,IndexError) as e:
            mark("provider_chat_result","FAIL",reason=type(e).__name__)
    # Genuine MP3 returned by real TTS, passed to real STT. Neither bytes nor transcript is logged.
    tts=await http_call(http,"provider_tts","POST",base+"/audio/speech",headers=headers,
        json_body={"model":"tts-1","voice":"alloy","input":"Приглуши свет","response_format":"mp3"},timeout=70)
    if tts is None or tts.status_code!=200:return
    audio=tts.content
    if len(audio)<250 or not (audio.startswith(b"ID3") or audio[:2] in (b"\xff\xfb",b"\xff\xf3",b"\xff\xf2")):
        mark("provider_tts_audio","FAIL",reason="Non-MP3 or empty")
        return
    mark("provider_tts_audio","PASS",byte_count=len(audio),media_type=tts.headers.get("content-type","").split(";")[0])
    stt=await http_call(http,"provider_stt","POST",base+"/audio/transcriptions",headers=headers,
        data={"model":"gpt-transcribe","language":"ru","response_format":"json"},
        files={"file":("sample.mp3",audio,"audio/mpeg")},timeout=90)
    if stt is not None and stt.status_code==200:
        try:
            transcription=stt.json()["text"]
            score=SequenceMatcher(None,transcription.lower().strip(" .!?"),"приглуши свет").ratio()
            mark("provider_stt_accuracy","PASS" if score>=.7 else "PARTIAL",
                 similarity=round(score,3),nonempty=bool(transcription))
        except (KeyError,TypeError,ValueError):
            mark("provider_stt_accuracy","FAIL",reason="Invalid transcription JSON")

async def main():
    async with httpx.AsyncClient(trust_env=False,follow_redirects=False) as http:
        try: await official(http)
        except Exception as e: mark("official_unhandled","FAIL",reason=type(e).__name__)
        write()
        try: await provider(http)
        except Exception as e: mark("provider_unhandled","FAIL",reason=type(e).__name__)
        write()

if __name__=="__main__":
    asyncio.run(main())
