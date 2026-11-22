# SAIN Stage 2 — Regression Matrix

Every PASS refers only to its named test and exact SHA; green on one feature branch does **not** establish combined behavior.

| System / Stage 1 invariant | Representative existing checks | Stage 2 addition | Integrated status |
|---|---|---|---|
| Temporal consistency, out-of-order reads | `tests/stage1/test_mr_new01_temporal.py`, `test_integrated_dst_scheduler_red.py` | Synthetic timezones + DST | PARTIAL (integrated CI pending) |
| Cancellation safety | `tests/stage1/test_mr_new04_cancellation.py`, `test_mr_new04_matrix.py` | No code changes to execute/cancel | PARTIAL (integrated CI pending) |
| HTTP422 definitive rejection | `tests/stage1/test_mr_new06_definitive.py`, frontend `stage1-definitive-rejection` | Invalid-value text improvement | PARTIAL (integrated browser CI pending) |
| Idempotency/replay | `tests/stage1/test_session_post_retries.py`, `test_mr_new04_matrix.py` | No mutation protocol modifications | PARTIAL |
| Partial / uncertain saga | `tests/stage1/test_partial_operations.py`, `tests/test_integration.py` | No simulator write path changed | PARTIAL |
| R1–R8, R6 late stay | `tests/test_logic.py`, `scripts/sleep_audit.py`, `tests/stage1/test_r6_short_stay.py` | Explicit R6 impossibility explanation | PARTIAL |
| Profile/history isolation | `tests/test_logic.py`, `tests/test_conversation.py` | Evidence-content cache + per-guest test | PARTIAL |
| 19 categories and no extraneous changes | `scripts/check_offline.py` (ScriptedModel) | Independent structured action oracle | PARTIAL; no live NLU score |
| Six device actual state | `backend/room.py` GET full-state equality | Explanations say 'planned' only | PARTIAL |
| React TS/Node/Vite/Playwright | `frontend/tests/*` + `frontend.yml` | Planned explanation text on two layouts | PARTIAL |
| Windows ZIP checksum | `windows-package.yml` | Same original Windows scripts | PARTIAL; native run NOT TESTED |
| Python/npm dependency audits | `.github/workflows/test.yml`, `frontend.yml` | Same dependencies | PARTIAL; only exact integration SHA counts |
| Server-only official /run & token safety | `scripts/check_offline.py`, `scripts/offline_guard.py` | No official network use | PARTIAL |

**Do not** drop old test files, substitute external service checks or conflate feature-SHA CI with integration-SHA CI.
