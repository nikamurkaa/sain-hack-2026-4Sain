# SAIN Smart Room — Stage 2 Implementation Report
Date: 2026-11-22. Official basis: Case 2 §§1–10 (16.11.2026), Instructions (16.11.2026).
Original main: `2ccad73652a20f93eb93e70e466e958cc731d705`. Integration base is the original main. No merge to main.

## Changes implemented
| Area | Code | Evidence | Status |
|---|---|---|---|
| 19 intent action categories | `tests/stage2/test_action_benchmark.py` | Independent complete-state oracle and expected response class, PR #22 | PARTIAL — no genuine NLU measurement |
| Negative, ambiguous, bounds | same | 10 refusal/ambiguity/conflict cases | PARTIAL — structured executor only |
| Multi-step action sequence | same | Unexpected sequence and unchanged-field comparison | PARTIAL — structured executor only |
| Sleep/time matrix | `tests/stage2/test_synthetic_journeys.py` | 32 synthetic zone/preference combinations + 2 DST transitions; additional 24 independently specified R1–R8 overnight cases | PARTIAL — independent full R1–R8 reference not yet created |
| Golden sleep-rule oracle (24 cases) | `tests/stage2/test_sleep_criteria_matrix.py` | Two explicit R8 bedtimes × 3 temperatures × 2 sound modes × 2 alarm modes; independent R1–R7 audit | PARTIAL until integrated SHA checks |
| Personalized evidence freshness | `backend/preferences.py` | Cache keys now contain user/profile and evidence content; Stage 2 regression test | PASS after exact-SHA Python CI, pending integrated proof |
| Privacy/guest isolation | `backend/core.py`, `backend/preferences.py` | Existing per-user evidence filter + new regression | PARTIAL — in-process scope only |
| Explainable scenarios | `backend/explanations.py`, `main.py`, `backend/api_models.py` | Planned reasons for 6 systems, source category, R6 warning; React plan/profile | PARTIAL until integrated browser CI |
| Precise invalid-value refusal | `backend/commands.py` | Named device value ranges in deterministic refusal | PARTIAL until integrated CI |
| Confirmed device state | Stage 1 `backend/room.py`, `main.py` | Reconciled GET /state; no false `done` after partial action | PARTIAL until independent Stage 2 integration check |

## Root causes and validation
1. **Stale preference cache**: previous key used source ID/time, not edited text or user profile. Fix uses full per-user snapshot identity. Regression edits source text under the same ID/timestamp and edits profile, expecting new model calls. No separate archived RED run exists; RED→GREEN provenance remains **NOT TESTED**.
2. **No auditable explanation surface**: prepared plans previously contained source facts but no compact reasons. New read-only `explanations` field reports source category (profile/history/default/rules) and status `planned` or `warning`, never raw quote/ID or simulator confirmation.
3. **Impossible R6 window**: Stage 1 deliberately refused to backdate actions on check-in less than 15 minutes before wake. Stage 2 now explains this limitation as a warning, **not** as a passed sleep rule.
4. **Generic invalid-value refusal**: `invalid_value` no longer replies with an unrelated out-of-scope message.

## Exact-SHA CI evidence (before final documentation update)
At integrated code SHA `7a3efc7fa52d5a02312db254d75c4e049c783bf0`, [Python backend Actions](https://github.com/nikamurkaa/sain-hack-2026-4Sain/actions/runs/45055542536) reported **433 passed, 1 warning**; scripted offline 10/60 passed in normal and 1 CPU/512 MiB runs with C=S=x=1.0. [Windows package Actions](https://github.com/nikamurkaa/sain-hack-2026-4Sain/actions/runs/45055542576) succeeded. These are reproducible *local synthetic* tests, not official hidden SAIN scores or native Windows acceptance. Integrated browser run: [45055542555](https://github.com/nikamurkaa/sain-hack-2026-4Sain/actions/runs/45055542555).

## Explicit gaps
- Live NLU accuracy, typo robustness, compound instruction resolution, context and negative preference inference remain unproven without a real model and blind benchmark; Stage 3.
- Deterministic tests with fixed structured intents are not independent measurements of a model's ability to understand language.
- No standalone official-simulator action / end-to-end evaluation beyond existing isolated mock transport.
- `R6` cannot be fulfilled for impossible check-in windows; only surfaced honestly.
- Windows package CI is not proof of executing START/STOP on physical Windows.
- Existing Stage 1 S-002/S-024 persistence, S-008 upstream atomicity, S-023 IP/brand and S-014 history-secret audit risks remain open.
- External official services, tokens, expert handoff, merger and direct main writes explicitly prohibited.

**Final verdict: STAGE 2 — NOT READY.** See integration readiness and next-stage backlog.


---

## 2026-11-22 — Completion and targeted integration hardening

**Code snapshot under test:** `c7cb43b1f89e6fb283ddc7cd294ab18f2635eba1`. Main base remains `2ccad73652a20f93eb93e70e466e958cc731d705`. In the integrated tree, **9/9 PR #21 and 4/4 PR #22 changed files match their respective latest feature-branch blob SHAs exactly**, including the 24 golden nights. No blind re-merge was performed.

### Browser failure: root cause and RED→GREEN evidence

- **RED:** [Chromium CI attempt 1 on source `53d7546d`](https://github.com/nikamurkaa/sain-hack-2026-4Sain/actions/runs/45055737867) timed out at 45 s, `frontend/tests/screens.spec.ts:175` (46 passed, 1 failed). [Failure artifact](https://github.com/nikamurkaa/sain-hack-2026-4Sain/actions/runs/45055737867/artifacts/14766964369) was downloaded and inspected. It contains captures through `evidence/28.png`, the profile/room/chat responsive captures and a final error-context snapshot still at the chat screen, but no `29.png` final-expiry frame.
- The old monolithic test combined initial loading, three settings screens, several simulated messages, an aborted POST, explicit reconnect, microphone review, multiple viewport screenshots and 401 expiry into **one** 45-second budget. No specific failed backend assertion was recorded. Starlette `No response returned` messages appeared during requests/disconnects; the stack traces alone do not establish causality.
- **Independent reproducibility check:** reran the original failed job **on the unchanged source SHA** (same run, attempt 2), which returned **SUCCESS**. This is evidence of intermittent timing/budget exhaustion, not a deterministic product regression.
- **Fixture/test fix:** commit `d65c09e5139907bba742146582d14dca9a5f9441` split the long test into three independent journeys while preserving the original checks and screenshot targets. No timeout extension, disabled test, artificial sleep or weakened assertion. [Exact-SHA Chromium + Firefox CI](https://github.com/nikamurkaa/sain-hack-2026-4Sain/actions/runs/45061740676) succeeded with **49/49 each**.
- A second **RED test-fixture failure** at `eb8491de`: 475 passed/1 failed because a newly synthesized note omitted the official dataset's required `type` and `ended_at`. This was test-fixture invalidity, not product behavior. Commit `c69b29ac37e743566bcadae5926d762b12c572d7` corrected the event schema; [Python CI](https://github.com/nikamurkaa/sain-hack-2026-4Sain/actions/runs/45062162529) returned **476 passed, 1 warning**, plus both normal and bounded offline 10/60.

### Additional integrated acceptance tests

| Gate | Exact test path | Independent oracle / observed effect | Scope status |
|---|---|---|---|
| All 19 categories | `tests/stage2/test_simulator_full_state.py` | Local FastAPI → MockSimulator; handwritten 6-device expected snapshots, done/refused, upstream POST counts | PASS within scripted category input |
| Device limits | same | Six fields × min/max; identical response/GET state, unchanged unrelated fields | PASS local |
| Stateful requests | same | Cool → cool again → bedtime → warmer → all off, compare all fields after each action | PASS local |
| Personalization | `tests/stage2/test_personalization_scenarios.py` | Profile vs history, newest hotel behavior, transient note, dislikes, no evidence, two identical IDs, actual home/yesterday commands | PASS in fixed test-extractor conditions |
| Simultaneous sessions | `tests/stage2/test_simulator_full_state.py` | Two distinct users, independent source-based temperature and concurrent FastAPI manual POSTs; simulator states isolated | PASS local |
| Faults | `tests/stage2/test_fault_injection_gate.py` | Accepted first action/rejected second, lost response after accepted POST, cancellation, 422, same-key concurrent send, GET reconciliation | PASS local |
| Sleep scenarios | `test_sleep_criteria_matrix.py`, `test_synthetic_journeys.py` | 24 golden R1–R8 nights, 32 cross-zone combinations, explicit Berlin DST, 10/60 regression | PASS for realizable scripted conditions |
| React explanations | `frontend/tests/stage2-explanations.spec.ts` | Local backend six-source preparation and mobile/desktop rationale; actual room state from GET | PENDING final browser CI |

**Boundaries:** Real NLU/LLM, adversarial unseen Russian text and STT are Stage 3, not measured here; private 86-item holdout is kept outside GitHub and never used to tune these tests. An R6 interval earlier than check-in is physically impossible and correctly marked as a warning. Native Windows execution, external API entitlement, durable multiworker recovery and production operation are not claimed.

The earlier **NOT READY** verdict above reflects an older integration head. A final acceptance decision must be taken from the exact HEAD outcomes and signoff table in `SAIN_Stage2_Integration_Readiness.md` and PR #23, not from historical CI.
