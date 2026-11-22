# Stage 3 — security and regression

**Status:** PARTIAL; latest SHA-specific CI results to be checked before acceptance. Baseline `main`: `4941f0be9a6531b553aeb50cccc75d4fd2c433e8`.

## Security invariants
- The attached `team25.zip` includes team secrets; none is committed, logged or placed in the portable ZIP by this implementation.
- Provider requests are backend-only; browser uses a separate guest token. No raw private dataset or closed benchmark is included.
- Strict Pydantic intent validation and deterministic planning remain the trust boundary.
- All action POSTs maintain existing idempotency/reconciliation logic; no unsafe retry on uncertain accepted POST is introduced by TTS or STT.
- TTS takes **recorded reply index**, not a user-supplied arbitrary string; repeated playback is local cached audio.
- STT only fills an editable draft and never acts automatically.
- Live mode is visibly labeled **real AI + local simulated devices**; no official final endpoint is modified.
- The new provider probe stores only sanitized metrics in `stage3-live-evidence.json`, excluding datasets, audio, transcripts, tokens and untrusted error bodies.

## Automated checks
| Area | Status | Source |
|---|---|---|
| Python full pytest & offline 10/60 | Earlier Stage 3 PR SHA(s) green; final HEAD pending | GitHub `test.yml` |
| New TTS adapter tests | Added under `tests/test_stage3_voice.py`; verify final CI | Draft branch |
| TypeScript + Node tests + Chromium/Firefox | CI running/re-run following JSX fix | GitHub `frontend.yml` |
| Windows ZIP checksums | CI `windows-package.yml`, both offline and LIVE archive | CI artifact only; native Windows NOT TESTED |
| Dependency audits, secret scan | Existing `test.yml` / `frontend.yml`; final result pending | CI logs |
| Official dev / real NLU / STT / TTS | NOT TESTED | Network/secret blockers |

**Known fixed regression in development:** TypeScript JSX expression in the new AI evidence panel initially failed CI at SHA `38229cc797166d313ed18800992a17fc1bba65c8`; addressed by later commit `926b84324ecc8835477beaee3d66bfbb8127fbef`. Do not treat the earlier failed run as a PASS.

## Remaining security tests
Independently test prompt injection, wrong intent, invalid/missing LLM JSON, missing parameters, timeout, expired key, rate/budget exhaustion, STT/TTS failure, double submission, session switching during speech, abort, cancellation after POST, guest isolation and reconciliation without retry. Unless exact SHA and evidence are attached, status remains NOT TESTED rather than silently passing.
