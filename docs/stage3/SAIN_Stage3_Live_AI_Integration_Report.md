# Stage 3 — live AI integration review

**Status:** CODE INTEGRATED IN DRAFT PR, FULL LIVE E2E NOT VERIFIED.

`React → localhost proxy → FastAPI → ModelClient(gpt-6-luna) → Pydantic Intent → deterministic Planner → local Simulator → authoritative state → React`.

## Implemented
- New `scripts/live_client.py` starts **real Bifrost ModelClient** for all user requests and STT, while using the isolated local synthetic room simulator. **No official room simulator is silently substituted.** The synthetic **bootstrap** of the local fixture remains deterministic and is explicitly disclosed as a synthetic demo profile.
- `scripts/rehearse_client.py` retains old completely offline FakeLLM mode. The live mode preserves operator-provided `LLM_API_KEY`, `LLM_MODEL`, `LLM_BASE_URL`, never puts keys into frontend or repository.
- Backend `ModelClient` parses JSON with `finish_reason=stop` and tracks only successful chat/STT/TTS replies, never raw prompts or transcripts. `backend/intents.py` validates via strict Pydantic. `backend/runner.py` applies deterministic commands, room state confirmation and safe refusal.
- `/api/v1/ai-status` reveals **only** current process model label, success counters and simulated-vs-external device label, authenticated by the guest token. Counters are **adapter receipts**, not an official provider audit.
- Real TTS is restricted to server-stored confirmed replies. Cached MP3 replay does not trigger /messages or room/action.
- `frontend/serve.py` explicitly labels `live` vs `rehearsal` and proxies only allowlisted paths on loopback. Windows launcher **mode 3** requests authorized key without echo.

## Gaps
- Neither local sandbox nor GitHub CI obtained real authorized provider/official API success, so no real live integration claim.
- Official dev dataset/reference was not obtained; no real official simulator action or C/S/x calculation.
- Real browser microphone, audio playback and native Windows acceptance remain open.
- New CI, dependency scan and E2E must be associated with the **final PR head SHA**, not earlier green builds.
- Hotel devices are **not** genuine physical devices, and no SAIN home synchronization API was accessed.

## Extra customer wishes
1. **Voice**: UI and backend path implemented; real acceptance NOT TESTED.
2. **Preparation within 10 seconds**: existing scenario planner present; **uncached real-data end-to-end latency NOT MEASURED**.
3. **Продолжение дома**: no officially authorized external SAIN synchronization contract confirmed; **NOT IMPLEMENTED**, do not present an imitation as real integration.

## Next verification
Run the authorized probe with secrets available **outside Git**, measure each provider call, then execute full browser text→voice→TTS with recorded six-device diffs and fresh CI. Keep final/read-only protection unchanged.
