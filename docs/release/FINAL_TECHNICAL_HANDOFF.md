# SAIN Smart Room — Technical Release Candidate Handoff
**Date:** 2026-11-23. **Branch:** `release/final-technical-completion`. **PR:** [#27](https://github.com/nikamurkaa/sain-hack-2026-4Sain/pull/27), Draft until all gates are proved.

## Provenances and current scope
- Stage 4 (29 React/Figma-derived states, 8 viewport browser coverage, a11y hardening) merged via [PR #26](https://github.com/nikamurkaa/sain-hack-2026-4Sain/pull/26) at main SHA `574e60eae29c9d57bcf0bafc62ee17714dca128e`. The reviewed original Stage 4 head `5da4b738db37ffbcdd7cc11908a2c0e3c2140b8a` has successful Python, Chromium/Firefox, and Windows ZIP CI, but **not native phone testing**.
- The release branch adds macOS offline and opt-in LIVE launchers, reproducible ZIP/checksums, native macOS Actions, Windows/browser workflow reruns, offline "Продолжение дома" with confirmed-device-state copy and synthetic checkout, and a full reachable-history secret-heuristic gate.
- `frontend/src/design/frames.json` and `art-01.svg`–`art-29.svg` remain the original visual baseline. LIVE Figma parity and native iOS/Android input/accessibility remain NOT TESTED.
- The local ROOM is a synthetic software simulator, **not** a real hotel device or official SAIN integration. Official tournament keys expired; no official API traffic or secrets have been used in this release candidate.

## Validated modes / limits
| Mode | Technical boundary | Acceptance rule |
|---|---|---|
| OFFLINE DEMO | `python -m scripts.rehearse_client`, local synthetic guests + deterministic interpretation; no external AI | Verify real local frontend + FastAPI via browser E2E, confirmed device state, no hidden provider calls |
| LIVE AI | `python -m scripts.live_client`, operator-controlled provider credentials in server environment; local ROOM | Code/loopback contract is not evidence of a genuine provider 200. Chat, STT, TTS must be marked NOT TESTED until separately authenticated |
| OFFICIAL SAIN | Original organizer backend, old event-scoped run/token | Access not authorized post-event. BLOCKED; never retry expired credentials or bypass final 409 |
| Voice | MediaRecorder → local STT → user review → action → verified state → reply TTS | Browser fake-STT tests do not establish real transcription, MP3 decoding or mobile microphone behavior |
| Windows | ZIP and native `windows-latest` smoke workflow | A Linux ZIP build does not establish Windows startup |
| macOS | `bash macos/START.command`, `bash macos/STOP.command`; built ZIP contains root `.command` files | `macos-latest` must genuinely start backend/frontend, issue guest, shut down and restart. Intel hardware is NOT TESTED |

## Exact-SHA verification procedure
The **PR head** is the only valid release SHA; check at [PR #27 checks](https://github.com/nikamurkaa/sain-hack-2026-4Sain/pull/27/checks). Required workflows: `Python backend and offline scenario`, `React TypeScript browser regression`, `Build portable Windows demo`, `Native Windows launcher smoke`, `Native macOS demo and package`. Confirm every run's `head_sha` equals current PR head; do not inherit success from an older commit. Download both Windows and macOS Actions ZIPs, inspect ZIP manifest, `BUILD_INFO.txt` source SHA and external `.sha256`. Native macOS hosted CI validates its runner architecture, not every Mac.

## Deployment (no real tokens)
- Windows: extract the Windows ZIP, run `CHECK_ENV.cmd`, then `START.cmd` and choose `1` REHEARSAL. `STOP.cmd` stops this installation.
- macOS: extract ZIP, run `bash CHECK_ENV.command` then `bash START.command`. Stop with `bash STOP.command`.
- In either offline mode, obtain an ephemeral LOCAL GUEST token from `.venv/bin/python -m scripts.client_access dev --stay stay_test` (Windows: `.venv\Scripts\python.exe -m scripts.client_access dev --stay stay_test`) and paste **only that guest token** into the browser.
- Live backend keys must never enter the browser, source, logs or artifacts. Network-bound provider proof must be independently obtained using valid *new* authorizations.

## Nonnegotiable release boundaries
1. **OFFLINE-only SQLite recovery is now implemented** for the standalone local demo. The loopback `scripts.rehearse_client` entrypoint defaults to `.sain-state/demo.sqlite3` (override `SAIN_DEMO_STATE_DB`). Session hashes/expiration, confirmed state, bounded dialogue, scenario, idempotency reservations, uncertain Room operations and synthetic simulator actions are checkpointed. A pending operation after crash stays uncertain; it is **not** reissued. Real/official provider APIs are NOT covered by these guarantees. LIVE still has in-memory sessions.
2. Current Stage 4 phone keyboard overlap, WCAG screen reader audit, 400% zoom and current live Figma difference are not independently closed.
3. Full historical Git/secret audit is a heuristic on reachable fetched refs; not private, deleted/unreachable Git objects, external runner secrets or absolute proof of no credentials. Any finding requires human-led rotation/evidence, **never a history rewrite** in this PR.
4. External approval registry `EXTERNAL_APPROVALS.md` says SAIN names/assets/official data/API continued public distribution and expert handoff need permission. A runnable local demo is not automatic permission for publication/distribution.
5. R1–R8/19 intents/10 guests and 60 requests are verified by the synthetic offline oracle when Python CI passes; no claim about official hidden benchmark accuracy or latency.
6. The `Продолжение дома` page copies confirmed synthetic device settings only and ends a **local guest session**; it does not check out from a real hotel or persist a future preference profile.

**Decision:** PR #27 stays Draft until exact final-head CI and independent review are green, release evidence is inspected, the tested demo route is complete and any mandatory blocker is resolved. Do not merge for presentation convenience. Next user-facing tasks (README rewrite, video, slides, public delivery) are intentionally out of scope.

## SQLite state recovery and operator controls (offline ONLY)
- `scripts/demo_persistence.py`: SQLite user_version=1, WAL + FULL synchronous commits, restricted local file permissions, `secure_delete`, epoch deadlines translated back to monotonic on restart. A missing database is initialized; a corrupt/unsupported DB prevents startup without silently resetting records. This is a **single local process** contract, not cross-instance coordination.
- Saved session tokens are **SHA-256 hashes**, never raw tokens; original browser guest token must be entered again after reload. Guest records retain local synthetic stay and bounded context, latest confirmed device state, scenario, 100 maximum idempotency decisions and Room operation journal. No real audio/AI provider credentials/official dataset are written. Local message content is private; never upload `.sain-state` to GitHub or distribute it.
- `Room` checkpoints operation intent and mutation-possible frontier **before** a device POST. Synthetic simulator fsyncs before a successful action response. Crash between send and receipt yields `ACTION_UNCERTAIN` and `reconciliation_required`, with a GET-only reconciliation endpoint. Confirmation receipts from an earlier completed key survive restart, but **do not imply global exactly-once** for any external device API.
- A confirmed simulated change survives clean/SIGKILL restart. Expired tokens are pruned; locally ended tokens are deleted; orphan synthetic room logs are removed on next startup. Even if an uncertain action is reconciled, a storage failure that could lose a device write blocks the session from new writes.
- For a deliberate reset on Windows: STOP.cmd → RESET_TEST_STATE.cmd → explicitly confirm deletion. On macOS: `bash STOP.command` then remove the local `.sain-state` directory **only if you intend to discard all synthetic data**. A normal restart never resets this database. Custom `SAIN_DEMO_STATE_DB` paths require deliberate operator cleanup after stop.
- Reproduce independent **real process** acceptance with `python -m scripts.check_persistence_process`: two guests + 6 devices, history + context, saved receipt, final read-only, clean restart, forced SIGKILL, expiry + close, deterministic before/after simulated POST process crashes and no action replay, DB corruption fail-closed. Additional tests `tests/test_persistence_failclosed.py` inject write failures. Chromium UI reconnect is exercised by `node frontend/scripts/check_persistence_browser.mjs` on the browser CI runner.
- Genuine remote-provider STT/TTS, official Sain device idempotency, shared DB across multiple workers, physical phone keyboards and external brand/IP permissions remain separately **NOT TESTED/BLOCKED**, not part of the offline technical acceptance.
