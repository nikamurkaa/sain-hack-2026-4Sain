# Stage 3 — Bifrost real provider smoke test

**Status: NOT TESTED.** Date: 2026-11-22 MSK. Source baseline: `4941f0be9a6531b553aeb50cccc75d4fd2c433e8`. Actual GitHub CI SHA: see linked run metadata.

| Test | Provider / model | Endpoint | Expected | Actual / evidence | Result |
|---|---|---|---|---|---|
| Credential authorization | Bifrost | GET /v1/models | HTTP 200 | Sandbox DNS `NameResolutionError`; PR workflow reports secret missing | NOT TESTED |
| Chat JSON | Bifrost / `LLM_MODEL` | POST /v1/chat/completions | 200, nonempty valid JSON, finish_reason=stop, usage | No authorized transport available | NOT TESTED |
| STT | Bifrost / gpt-transcribe | POST /v1/audio/transcriptions | 200, Russian text | No provider call | NOT TESTED |
| TTS | Bifrost / tts-1 | POST /v1/audio/speech | 200, valid nonempty MP3 | No provider call | NOT TESTED |
| Browser voice E2E | Browser → local FastAPI → Bifrost | local /api/v1/transcriptions, /messages, /speech | Live speech → state → live audio | Not recorded or demonstrated | NOT TESTED |

- At 2026-11-22 approximately 23:50 MSK, actual `GET /v1/models` was attempted with the uploaded AI key from a private in-memory ZIP read: **transport DNS failure, no HTTP response**. Key was never printed, committed or passed to GitHub.
- GitHub Actions run **45068829236** executed the bounded probe but reported `provider_auth: NOT TESTED`; `LLM_API_KEY` was not provided as a repository workflow secret. A green workflow means the diagnostic script ran, **not that Bifrost responded**.
- `scripts/stage3_provider_probe.py` can run authorized GET/models → chat → real TTS MP3 → real STT on that MP3 with sanitized evidence. The generated audio is real provider speech, not a human microphone recording. Live microphone acceptance is a separate gate.
- Required provider success metrics (HTTP status, latency, usage, finish reason, transcript comparison, MP3 decode) are **NOT AVAILABLE**; do not infer zeros or passes.
- Original AI key expiry from organizer instructions: **2026-11-23 12:00 MSK**. After expiry, obtain new authorized access; do not bypass.

**Evidence discipline:** Only successful real requests may be marked PASS. No fake provider transcript, sample MP3 or playback is accepted as evidence of real access.
