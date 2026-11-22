# SAIN Smart Room — Stage 2 Implementation Report
Date: 2026-11-22. Official basis: Case 2 §§1–10 (16.11.2026), Instructions (16.11.2026).
Original main: `2ccad73652a20f93eb93e70e466e958cc731d705`. Integration base is the original main. No merge to main.

## Changes implemented
| Area | Code | Evidence | Status |
|---|---|---|---|
| 19 intent action categories | `tests/stage2/test_action_benchmark.py` | Independent complete-state oracle and expected response class, PR #22 | PARTIAL — no genuine NLU measurement |
| Negative, ambiguous, bounds | same | 10 refusal/ambiguity/conflict cases | PARTIAL — structured executor only |
| Multi-step action sequence | same | Unexpected sequence and unchanged-field comparison | PARTIAL — structured executor only |
| Sleep/time matrix | `tests/stage2/test_synthetic_journeys.py` | 32 synthetic zone/preference combinations + 2 DST transitions | PARTIAL — independent full R1–R8 reference not yet created |
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

## Explicit gaps
- Live NLU accuracy, typo robustness, compound instruction resolution, context and negative preference inference remain unproven without a real model and blind benchmark; Stage 3.
- Deterministic tests with fixed structured intents are not independent measurements of a model's ability to understand language.
- No standalone official-simulator action / end-to-end evaluation beyond existing isolated mock transport.
- `R6` cannot be fulfilled for impossible check-in windows; only surfaced honestly.
- Windows package CI is not proof of executing START/STOP on physical Windows.
- Existing Stage 1 S-002/S-024 persistence, S-008 upstream atomicity, S-023 IP/brand and S-014 history-secret audit risks remain open.
- External official services, tokens, expert handoff, merger and direct main writes explicitly prohibited.

**Final verdict: STAGE 2 — NOT READY.** See integration readiness and next-stage backlog.
