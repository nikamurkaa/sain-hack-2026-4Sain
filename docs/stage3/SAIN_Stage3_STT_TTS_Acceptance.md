# Stage 3 — live microphone / STT / TTS acceptance

**Status: IMPLEMENTED IN CODE / LIVE NOT TESTED.** No successful authenticated provider audio request or complete microphone-to-playback scenario verified at the time of authoring.

## STT
`frontend/src/Voice.tsx` already has MediaRecorder, recording status, stop, cancel, limited size and duration, editable transcription and explicit submit. `main.py /api/v1/transcriptions` validates MIME and 5 MB, calls `ModelClient.transcribe` → real Bifrost `gpt-transcribe` **only in LIVE mode**; offline rehearsal separately uses `RehearsalModel`. STT **never executes an action** before user confirmation.

## TTS
Stage 3 adds `ModelClient.speak` → Bifrost `tts-1`, MP3 checks, 402/429 handling; `POST /api/v1/speech` takes only a server-recorded `reply_index`. It does not accept arbitrary model texts or execute device POST. Desktop dialogue and mobile history show `SpeechReply` controls: play, stop, repeat cached MP3, mute, error fallback without losing text. There is a single active-audio guard.

## Cases that require real acceptance
| Case | Expected | Status |
|---|---|---|
| Real browser microphone → WebM/MP4 → provider STT | Valid Russian transcription | NOT TESTED |
| Transcript preview & edit | No auto action until explicit confirmation | CODE PRESENT; browser live NOT TESTED |
| Confirmed text → provider chat → validated intent | Model success and strict parameters | NOT TESTED |
| Planner → local simulator → full state | Confirmed six-device snapshot, no unwanted changes | NOT TESTED live |
| Recorded reply → provider TTS → actual MP3 playback | Heard and decoded voice | NOT TESTED |
| Stop / replay / mute | No repeated action POST | Offline code/test only |
| Microphone denied / abort / empty / wrong MIME / 5 MB+ | Safe error, no action | Existing guards; browser re-acceptance pending |
| 402 / 413 / 429 / timeout / expired / session replacement | Specific safe failure, no silent FakeLLM fallback | Not all cases independently tested |

**Official constraints**: STT `gpt-transcribe`, `language=ru`, `response_format=json`; TTS `tts-1`, `voice=alloy`, MP3; uploads under 5 MB; input under 4096 characters; 10 voice calls/minute per kind (shared overall 30/min).
**Real call proof**: timestamp, exact source SHA, endpoint (never authorization), HTTP status, latency, byte length/transcription quality and provider receipt, without raw audio or private transcript.
