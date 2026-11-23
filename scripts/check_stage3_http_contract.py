"""Contract smoke test for LIVE AI against a LOCAL HTTP provider emulator.

No organizer token, public API, Bifrost request, or real AI is used.
Deliberately runs OUTSIDE pytest: pytest's global offline guard blocks ALL
socket connections, including the loopback transport under test.
"""
import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from fastapi.testclient import TestClient

from scripts.rehearse_client import build_rehearsal
from tests.helpers import AT


def main():
    recorded = []
    flags = {"intent": "cooler", "stt": 200, "tts": 200}

    class LocalProvider(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def do_POST(self):
            body = self.rfile.read(int(self.headers.get("Content-Length", "0")))
            recorded.append((self.path, self.headers.get("Authorization"), len(body)))
            status, media = 200, "application/json"
            if self.path == "/v1/chat/completions":
                payload = json.loads(body)
                user = json.loads(payload["messages"][-1]["content"])
                output = ({"intent": flags["intent"]} if "utterances" in user
                          else {"facts": []})
                result = {"choices": [{"finish_reason": "stop", "message": {
                    "content": json.dumps(output)}}], "usage": {"total_tokens": 11}}
                content = json.dumps(result).encode()
            elif self.path == "/v1/audio/transcriptions":
                status = flags["stt"]
                content = json.dumps({"text": "Сделай попрохладнее"},
                                     ensure_ascii=False).encode()
            elif self.path == "/v1/audio/speech":
                status = flags["tts"]
                content = b"ID3" + bytes(700)
                media = "audio/mpeg"
            else:
                status, content = 404, b"{}"
            self.send_response(status)
            self.send_header("Content-Type", media)
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)

    server = ThreadingHTTPServer(("127.0.0.1", 0), LocalProvider)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    os.environ["LLM_API_KEY"] = "LOCAL-CONTRACT-KEY-ONLY"
    os.environ["LLM_MODEL"] = "gpt-6-luna"
    os.environ["LLM_BASE_URL"] = f"http://127.0.0.1:{server.server_address[1]}/v1"
    try:
        with TestClient(build_rehearsal(live=True)) as client:
            initial = client.post("/api/v1/sessions", headers={
                "Authorization": "Bearer offline-team"
            }, json={"source": "dev", "stay_id": "stay_test",
                     "dataset_code": "case2-dev-v1"})
            assert initial.status_code == 201, initial.text
            headers = {"Authorization": "Bearer " + initial.json()["session_token"]}
            from main import app as backend
            before = client.get("/api/v1/state", headers=headers,
                                params={"at": AT}).json()["state"]
            actions_before = backend.state.rehearsal_simulator.actions

            transcription = client.post("/api/v1/transcriptions",
                                        headers={**headers, "Content-Type": "audio/webm"},
                                        content=b"LOCAL-TEST-AUDIO-NOT-REAL-SPEECH")
            assert transcription.status_code == 200, transcription.text
            assert transcription.json()["text"] == "Сделай попрохладнее"
            assert backend.state.rehearsal_simulator.actions == actions_before, "STT executed a command!"

            command = client.post("/api/v1/messages",
                                  headers={**headers, "Idempotency-Key": "contract-live-001"},
                                  json={"text": transcription.json()["text"], "at": AT})
            assert command.status_code == 200, command.text
            assert command.json()["reply"]["response_class"] == "done"
            state = command.json()["state"]
            assert state["climate"]["temperature_c"] == before["climate"]["temperature_c"] - 1
            for device in ("light", "sound", "curtains", "alarm", "dnd"):
                assert state[device] == before[device], f"Unexpected mutation: {device}"
            assert backend.state.rehearsal_simulator.actions == actions_before + 1

            tts = client.post("/api/v1/speech", headers=headers, json={"reply_index": 0})
            assert tts.status_code == 200
            assert tts.headers["content-type"] == "audio/mpeg"
            assert tts.content.startswith(b"ID3")
            assert backend.state.rehearsal_simulator.actions == actions_before + 1

            counts = client.get("/api/v1/ai-status", headers=headers).json()
            assert counts["mode"] == "live" and counts["devices"] == "local_simulator"
            assert counts["successful_calls"]["chat"] >= 2
            assert counts["successful_calls"]["stt"] == 1
            assert counts["successful_calls"]["tts"] == 1

            flags["stt"] = 429
            busy = client.post("/api/v1/transcriptions",
                               headers={**headers, "Content-Type": "audio/webm"},
                               content=b"LOCAL-AUDIO")
            assert busy.status_code == 429, busy.text
            assert backend.state.rehearsal_simulator.actions == actions_before + 1

            flags["tts"] = 402
            no_budget = client.post("/api/v1/speech",
                                    headers=headers, json={"reply_index": 0})
            assert no_budget.status_code == 402, no_budget.text
            assert backend.state.rehearsal_simulator.actions == actions_before + 1

            flags["intent"] = "invalid_provider_intent"
            invalid = client.post("/api/v1/messages",
                                  headers={**headers, "Idempotency-Key": "contract-live-invalid"},
                                  json={"text": "Отладка невалидного ответа", "at": AT})
            assert invalid.status_code >= 400, invalid.text
            assert backend.state.rehearsal_simulator.actions == actions_before + 1
            assert len(client.get("/api/v1/session", headers=headers).json()["history"]) == 1

        paths = [entry[0] for entry in recorded]
        assert paths.count("/v1/audio/transcriptions") == 2
        assert paths.count("/v1/audio/speech") == 2
        assert paths.count("/v1/chat/completions") >= 3
        assert all(entry[1] == "Bearer LOCAL-CONTRACT-KEY-ONLY" for entry in recorded)
        print("STAGE3 LOCAL HTTP CONTRACT: PASS (chat, STT, TTS, state, errors, no duplicate actions)")
        return 0
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


if __name__ == "__main__":
    raise SystemExit(main())
