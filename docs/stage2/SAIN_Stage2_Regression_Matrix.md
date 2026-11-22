# SAIN Stage 2 — Regression Matrix

Every PASS refers only to its named test and exact SHA; green on one feature branch does **not** establish combined behavior.

| System / Stage 1 invariant | Representative existing checks | Stage 2 addition | Integrated status |
|---|---|---|---|
| Temporal consistency, out-of-order reads | `tests/stage1/test_mr_new01_temporal.py`, `test_integrated_dst_scheduler_red.py` | Synthetic timezones + DST | PARTIAL (integrated CI pending) |
| Cancellation safety | `tests/stage1/test_mr_new04_cancellation.py`, `test_mr_new04_matrix.py` | No code changes to execute/cancel | PARTIAL (integrated CI pending) |
| HTTP422 definitive rejection | `tests/stage1/test_mr_new06_definitive.py`, frontend `stage1-definitive-rejection` | Invalid-value text improvement | PARTIAL (integrated browser CI pending) |
| Idempotency/replay | `tests/stage1/test_session_post_retries.py`, `test_mr_new04_matrix.py` | No mutation protocol modifications | PARTIAL |
| Partial / uncertain saga | `tests/stage1/test_partial_operations.py`, `tests/test_integration.py` | No simulator write path changed | PARTIAL |
| R1–R8, R6 late stay | `tests/test_logic.py`, `scripts/sleep_audit.py`, `tests/stage1/test_r6_short_stay.py` | Explicit R6 impossibility explanation; 24 independent R1–R8 golden overnight checks | PARTIAL |
| Profile/history isolation | `tests/test_logic.py`, `tests/test_conversation.py` | Evidence-content cache + per-guest test | PARTIAL |
| 19 categories and no extraneous changes | `scripts/check_offline.py` (ScriptedModel) | Independent structured action oracle | PARTIAL; no live NLU score |
| Six device actual state | `backend/room.py` GET full-state equality | Explanations say 'planned' only | PARTIAL |
| React TS/Node/Vite/Playwright | `frontend/tests/*` + `frontend.yml` | Planned explanation text on two layouts | PARTIAL |
| Windows ZIP checksum | `windows-package.yml` | Same original Windows scripts | PARTIAL; native run NOT TESTED |
| Python/npm dependency audits | `.github/workflows/test.yml`, `frontend.yml` | Same dependencies | PARTIAL; only exact integration SHA counts |
| Server-only official /run & token safety | `scripts/check_offline.py`, `scripts/offline_guard.py` | No official network use | PARTIAL |

**Do not** drop old test files, substitute external service checks or conflate feature-SHA CI with integration-SHA CI.


---

## Completion hardening — exact test paths and local evidence

| Acceptance axis | Regression / new test | GitHub evidence | Status at local scope |
|---|---|---|---|
| Baseline Stage 1 cancellation/temporal/idempotency | `tests/stage1/test_mr_new04_matrix.py`, `test_mr_new01_temporal.py`, `test_mr_new06_definitive.py` | [Python CI 476 passed](https://github.com/nikamurkaa/sain-hack-2026-4Sain/actions/runs/45062162529) | PASS |
| 19 categories, six device fields unchanged | `test_simulator_full_state.py` (19 parametrized FastAPI cases) | Same Python run | PASS local |
| Boundary/surprising sequence | Same (12 bound endpoints, 5-step room journey) | Same Python run | PASS local |
| Profile/history conflict and source edits | `test_personalization_scenarios.py` | Same Python run | PASS selected profiles |
| True multi-user isolation and concurrent POSTs | `test_simulator_full_state.py` | Same Python run | PASS local |
| First action accepted, second rejected | `test_fault_injection_gate.py` | Same Python run | PASS; partial not done |
| Accepted POST then lost reply + GET uncertainty | Same | Same | PASS; no blind retry |
| Cancelled POST after accept | Same and Stage 1 cancellation suite | Same | PASS; temporal floor held |
| Same key double-submit, changed payload | Same + Stage 1 | Same | PASS; exactly one actual POST per operation in-process |
| Past-time write before/after reconciliation | Same + Stage 1 | Same | PASS; 409 without POST |
| Definitive HTTP422 prehandler/domain | Same + Stage 1 | Same | PASS; zero POST, verified recovery |
| R1–R8 golden | `test_sleep_criteria_matrix.py` 24, synthetic 32+2 DST | Same | PASS realizable cases; impossible R6 PARTIAL |
| Scripted 10/60, normal and resource-bounded | `scripts/check_offline.py` | Same | PASS for offline simulator/fake model |
| Browser split, Chromium/Firefox | `frontend/tests/screens.spec.ts` now 3 independent journeys | [49 Chromium + 49 Firefox](https://github.com/nikamurkaa/sain-hack-2026-4Sain/actions/runs/45061740676) | PASS on split-fix SHA `d65c09e5` |
| Frontend stage2 prepared rationale | `frontend/tests/stage2-explanations.spec.ts` | Final integrated frontend CI on PR #23 | PENDING exact-head check |
| Python pip-audit, npm high+ advisory, Windows ZIP | Existing workflows and no dependency changes | Exact-head workflows required | PENDING last documentation SHA |
| Native Windows START/STOP, real operator/accessibility and remote upstream transactional guarantees | Not tested | None | NOT TESTED (Stage 6/7 and permissions) |

**Original failure:** 46 Chromium passed, 1 timeout at 45 s on `53d7546d`, all steps shared one long test. Repeat unchanged SHA passed; split green across both browsers, no timeout increase. ASGI disconnect stack traces do not on their own establish an independent backend bug. The confirmed code fix here targets E2E test isolation.
