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
