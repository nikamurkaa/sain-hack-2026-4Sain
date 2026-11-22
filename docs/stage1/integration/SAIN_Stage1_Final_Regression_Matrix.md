# SAIN Stage 1 — Final Integrated Regression Matrix

Source: [integration PR #20](https://github.com/nikamurkaa/sain-hack-2026-4Sain/pull/20).
**Never add test counts from separate PRs.** The final PR's HEAD and Actions checks are the only accepted combined verification SHA. The stable pre-documentation executable checkpoint `b29ad6381bd7ed755e7e18addbe766614907f715` is listed for traceability; report files add commits afterwards, so confirm the final SHA from PR metadata.

| Test family | Integrated source/test oracle | Verified scope / acceptance interpretation |
|---|---|---|
| Full backend pytest | `python -m pytest -q` | 284 passed at intermediate integrated SHA c6a8da64807e53129cd471c8cdce55121101f8ea, run [45023991424](https://github.com/nikamurkaa/sain-hack-2026-4Sain/actions/runs/45023991424); recheck latest final CI |
| Offline /run normal and constrained | `python -m scripts.check_offline` twice | 10 guests, 60 requests, 19 scripted intent variants, zero incorrect requests, R1–R8 no failed_rules, zero extra device changes, score x=1.0 in tested fixture |
| R6 short-stay 0–31m | `tests/stage1/test_r6_short_stay.py` | Normal 30/23/16 light or legal 15-minute curtain; <15m impossible is not claimed compliant |
| DST real UTC moments | `tests/stage1/test_integrated_dst_scheduler_red.py` | Berlin/NY spring/fall; Moscow control; *every* scheduled event validates date-correct IANA offset and UTC order |
| DST backend validation | `tests/stage1/test_dst_hotel_time.py` | Ambiguous fall-back offsets disambiguated, nonexistent spring-forward / stale offsets rejected |
| Frontend virtual preview | `frontend/tests/stage1-timezone.test.ts` and browser E2E | Date-specific timezone offsets; future GET is read-only vs confirmed snapshot |
| Non-atomic saga | `tests/stage1/test_partial_operations.py` | First/second/third step failure, lost reply, read timeout, drift/conflict and verified state |
| Cross-PR race/replay | `tests/stage1/test_cross_pr_integration_red.py` | API repeated partial error preserves metadata, concurrent distinct/same operation IDs, journal capacity, stable conflict/partial replays |
| Session-create unsafe retry | `tests/stage1/test_session_post_retries.py`, updated final-score gate | One POST under fault injection; do not invent a new session ID from a timeout/503 |
| Session isolation & read-only | `tests/test_conversation.py`, `test_manual_devices.py`, Playwright | Dev/final separation, token expiry, read-only refusal, 6 devices, schema and range checks |
| Guest identity | `frontend/tests/stage1-identity.spec.ts` | Actual localhost API without display_name, neutral heading, no Figma placeholder |
| History + errors / reconnect | `frontend/tests/journey.spec.ts`, `quality-history.spec.ts` | Real local backend, long history and network unknown delivery, no blind re-POST |
| Restart | `tests/test_rehearsal_recovery.py` | Old token invalid, new local session allowed; **durability not implemented** |
| Python vulnerabilities | `python -m pip_audit -r requirements.txt` | Public advisory query, no known vulnerabilities at checkpoint [45024072125](https://github.com/nikamurkaa/sain-hack-2026-4Sain/actions/runs/45024072125); does not prove absence of future/unknown findings |
| npm vulnerabilities | `npm audit --audit-level=high` | CI-gated locked graph; check final frontend job, not assumed here |
| Tracked secret candidates | `python -m scripts.stage1_security_gate` | Bounded text/filename detection with no value logging; not full Git history scan |
| Native Windows | Linux `windows-package.yml` + ZIP SHA256 | Package CRC/checksum on Linux; **native Windows execution unverified** |
| Live STT/LLM and official API | None by design | **NOT TESTED**; no organizer endpoints/tokens /run used |
| Combined code acceptance | PR #20, check runs at exact head | **Not inferable from separately green PR #14–19**; see PR checks |

## Red-to-green traceability

| Red SHA | Failed independent oracle | Fix SHA |
|---|---|---|
| 4f1ef19a15dabacd649c847875cd48afc3f48deb | 3 failures: lost partial metadata, concurrent room state race, journal key eviction | bfa67acce45288a4af1298dcc7e9be1fecca9199 and 709853ad57a724e484c1e89f5d99461f372b1cf9 |
| b1f34fb6f95cbfaf3086263170a0325167a4aa1b | 5 DST timeline violations of IANA/local offset | fe36cdc5197a1b254e1e0e4c8ef120f3c8fa31b0 |
| e6e613012b15cb0915943a04933bac30c11bf1bb | 2 replay/status classification failures | c6a8da64807e53129cd471c8cdce55121101f8ea |

All positive results in the matrix refer only to the local synthetic simulator. Re-run the full matrix at the **final integration HEAD** before declaring independent review ready.


---

## 2026-11-22: Independent MR-001–MR-004 remediation (PR #20)

This section supersedes any earlier *merge-readiness claim* in the original Stage 1 document; pre-remediation CI does not establish acceptance of the new HEAD. Full issue-by-issue proof, reproducible tests, red-green SHA links, scope and reviewer questions: [SAIN_Stage1_Merge_Review_Remediation.md](SAIN_Stage1_Merge_Review_Remediation.md).

| MR ID | New assertion/coverage | Test files | Before-fix proof | Green evidence/checkpoint |
|---|---|---|---|---|
| MR-001 | typed 409 metadata, malicious JSON fallback, known device names, true partial/unknown/conflict, single POST on idempotency replay, 375×812+1440×900 mobile/desktop and keyboard, GET success/failure, no false done | `frontend/tests/stage1-action-error.test.ts`, `frontend/tests/stage1-partial.spec.ts`, `tests/stage1/test_mr001_rehearsal_fault.py` | [red Node 45027331815](https://github.com/nikamurkaa/sain-hack-2026-4Sain/actions/runs/45027331815) missing ActionApiError, red after adding full-transport test [45027912975](https://github.com/nikamurkaa/sain-hack-2026-4Sain/actions/runs/45027912975) identified missing stale-GET expectation | [green combined 45027979302](https://github.com/nikamurkaa/sain-hack-2026-4Sain/actions/runs/45027979302) and [Chromium/Firefox 45027979275](https://github.com/nikamurkaa/sain-hack-2026-4Sain/actions/runs/45027979275), 28 each at code checkpoint; final PR HEAD evidence supersedes these |
| MR-002 | TestClient Berlin/NY spring gap and autumn fold, valid Moscow, before/after DST, next-day, same/different idempotency key, 0 simulator writes on reject | `tests/stage1/test_mr002_alarm_contract.py` | [red backend 45027331816](https://github.com/nikamurkaa/sain-hack-2026-4Sain/actions/runs/45027331816): four HTTP 500s | [green backend 45028432526](https://github.com/nikamurkaa/sain-hack-2026-4Sain/actions/runs/45028432526), final PR run required |
| MR-003 | New York first-fold bedtime preceding second-fold wake, earliest-fold choice, spring-gap forward resolution, real UTC ordering, +1/−1h R8, Berlin/NY/Moscow | `tests/stage1/test_mr003_bedtime_fold.py`, existing `test_integrated_dst_scheduler_red.py` | [red backend 45027331816](https://github.com/nikamurkaa/sain-hack-2026-4Sain/actions/runs/45027331816): two independent DST bedtime failures | [green 305 pytest 45028432526](https://github.com/nikamurkaa/sain-hack-2026-4Sain/actions/runs/45028432526), final PR run required |
| MR-004 | Assert non-merge source commit with job env and checkout ref | `.github/workflows/test.yml` (checkout and exact SHA assertion) | Original [CI 45024448298](https://github.com/nikamurkaa/sain-hack-2026-4Sain/actions/runs/45024448298) tested synthetic merge SHA; tree was identical, provenance policy still violated | [backend 45028432526](https://github.com/nikamurkaa/sain-hack-2026-4Sain/actions/runs/45028432526) now logs expected and actual exact head; verify final run against final SHA |

**Final exact-SHA gate:** resolve PR #20 head *after the final documentation commit*, then verify all three completed SUCCESS runs on that SHA. Do not interpret the above intermediate proof as independent signoff. Existing S-003/S-004/S-008/S-009/S-010, INT-001–INT-006 and the 10/60 offline score remain required regression checks.


---

## TEMPORAL FINAL GATE — MR-NEW-01/02/03 (2026-11-22)

> **Supersedes earlier review-ready claims based on `fb3b082...`.** The independent second review found a new P1 temporal inconsistency; the older 305/28-each green runs are **not** acceptance of the new code. Final disposition requires three new SUCCESS workflows whose jobs checked out the **same last PR HEAD**, independent signoff, and a separate owner merge decision. Full technical explanation: [SAIN_Stage1_Temporal_Recovery_Remediation.md](SAIN_Stage1_Temporal_Recovery_Remediation.md).

| Temporal T2!=T1 | `tests/stage1/test_mr_new01_temporal.py`, `frontend/tests/stage1-temporal.{test,spec}.ts` | RED `9eda085...` [45031450797](https://github.com/nikamurkaa/sain-hack-2026-4Sain/actions/runs/45031450797) (2 failed). Green code checkpoint [45032271808](https://github.com/nikamurkaa/sain-hack-2026-4Sain/actions/runs/45032271808) **311 pytest**, [45032271827](https://github.com/nikamurkaa/sain-hack-2026-4Sain/actions/runs/45032271827) **13 Node / 41 Chromium / 41 Firefox**; T2 partial light=0, stale T1=70, no T1 POST, no POST on GET, same key replay, manual uncertain, midnight, conflict, guest isolation, default/live/preview distinct |
| Untrusted recon snapshot | `frontend/tests/stage1-temporal.test.ts`, `frontend/tests/stage1-temporal.spec.ts` | Wrong operation ID/UTC instant/snapshot/confirmed devices HTTP200 rejected; same instant with different offset accepted; GET failure stays stale and no auto POST; async response generation guard |
| Mobile stale submit | `frontend/tests/stage1-temporal.spec.ts` | Nonempty draft disabled, aria-describedby, no retry, successful GET allows new manual send, no automatic submission; Figma decorative circle dimmed; 320×568 screenshot |
| In-flow critical notice | `frontend/tests/stage1-temporal.spec.ts` | 320×568, 360×640, 375×667/812, 390×844, 430×932, 768×1024, 1440×900 and 200% zoom; DOM focus/Enter, no horizontal overflow, dismiss then six devices, screenshots Chromium+Firefox |
| Windows ZIP test layout | `tests/test_quality_gate_time_ops.py` | Source under `windows/`, flattened release root with BUILD_INFO and START/STOP — 311 full pytest from exact ZIP **without symlink**, artifact contents unchanged |

**Final SHA policy:** all figures above identify a specific code checkpoint. The final documentation commit changes PR HEAD; only the *new* backend/frontend/Windows success checks linked in PR #20 constitute final exact-HEAD evidence. Never merge based on prior screenshots alone.


---

## MR-NEW-04 — cancellation safety supersedes earlier merge-readiness claims (2026-11-22)

**Independent reviewer verdict on old SHA `def405ffc0a8aceb9dc4c49d8206a1992b368f29`: REQUEST CHANGES BEFORE MERGE.** An asynchronous `CancelledError` after an upstream POST accepted at T2 left Session without floor/issue, enabling an unsafe T1 write. This is fixed in integration-only code and remains **pending independent signoff**. Full evidence, root cause, safe cleanup and test matrix: [SAIN_Stage1_Cancellation_Safety_Remediation.md](SAIN_Stage1_Cancellation_Safety_Remediation.md).

| MR-NEW-04 P1 cancelled POST, API | `tests/stage1/test_mr_new04_cancellation.py` | Original independent exact-SHA defect reproduced by supplied `independent_api_probes.py`; pre-main-fix [45036473916](https://github.com/nikamurkaa/sain-hack-2026-4Sain/actions/runs/45036473916) **3 failed**; green real TestClient cancellation for BOTH messages/devices; same-key replay zero extra POST, old T1 write blocked; separate independent bfff ZIP probe first HTTP500, same-key HTTP409, T1 HTTP409 before/after GET; upstream POST 1 until deliberate T2 action |
| MR-NEW-04 cancellation at awaited boundaries | `tests/stage1/test_mr_new04_matrix.py` | 12 parametrized async CancelledError checkpoints: before/after POST, before/after GET, after 1st/2nd action; preserve confirmed device subset without invented success, stable status/floor/key; failed GET, two guests, token expiry, midnight and timezone offset; new actual `Task.cancel()` x2 test proves Room lock release and replay safety |
| MR-NEW-04 lost response/browser | `frontend/tests/stage1-cancellation.spec.ts`, strengthened `frontend/tests/screens.spec.ts` | Real local FastAPI/MockSimulator accepted POST at T2; synthetic task cancellation & 3 failed GET; Chromium/Firefox assert stale disabled, no automatic retry, 1 upstream action, error on T1, same original key replay, reconnect with SAME guest token exposes pending, GET reconciliation and safe T2 new action; mock network abort cannot automatically authorize another write |
| MR-NEW-04 code checkpoint | `bfff9048c85340f63451bf2c5b373e65eb5ef8e7` | [backend 45037464859](https://github.com/nikamurkaa/sain-hack-2026-4Sain/actions/runs/45037464859) 330 passed, [frontend 45037464823](https://github.com/nikamurkaa/sain-hack-2026-4Sain/actions/runs/45037464823) 43 Chromium/43 Firefox, [Windows 45037464825](https://github.com/nikamurkaa/sain-hack-2026-4Sain/actions/runs/45037464825) success; **checkpoint only**, final docs-commit HEAD and new `Task.cancel()` test must be rechecked |

**Final provenance rule:** final exact HEAD and all three SUCCESS actions available from current Draft PR #20; do not reuse old `def405ffc...` green runs as acceptance of cancellation behavior.