# SAIN Stage 2 — Personalization and Preference Reasoning

## Current pipeline
1. `backend/core.py:evidence` filters events/chat by `user_id`, role, event completion and cutoff; no future note or other user's note may be presented to the extractor.
2. `backend/preferences.py:parse_facts` accepts only catalogue-compatible settings with source ID + **exact** substring quote; invalid fields are rejected, source repair requires unique quote provenance.
3. Resolved fields: night temperature class, sleep tracks/volume/timer, alarm mode, exact home/morning/yesterday device fields, source map and defaults. Historical statements need substantive validation by the model; exact quote presence is not semantic proof.
4. In current code, structured profile temperature/tracks take priority over extracted history values for the same key; remaining extracted keys use newest verified timestamp. `yesterday` requires matching local calendar date. This priority is an **implementation policy**, not a claim of universally correct semantics.
5. At prepare time, `build_scenario` creates R1–R8 actions; manual requests do not silently become permanent habits.

## Improvements
- Fixed stale source cache: cache key now includes per-user profile and note **content**, not only IDs/times. Changes to a note under the same ID/timestamp cannot return stale preference decisions.
- Added `/api/v1/prepared.explanations` for six devices: rule references, source category, planned-only status, and R6 constraint warning; raw notes and source IDs are not returned by this field.
- Added tests for edited notes, edited profile, cross-guest isolation, missing vs configured preferences, profile-dislike source class and unrealizable dawn.
- React displays planned reasons in plan/profile and mobile without replacing GET-verified actual device state.

## Unresolved, with honest scope
| Concern | Status | Required follow-up |
|---|---|---|
| Temporal habits vs persistent changes | PARTIAL | Independent multi-stay, negative and temporary-change semantic datasets |
| Conflicting profile and observed hotel habits | PARTIAL | Document evidence priority and operator override policy, blinded evaluation |
| `like_yesterday` / `like_home` inference | PARTIAL | Real-model multilingual/colloquial benchmark; current test checks structured plan |
| Missing data | PARTIAL | Explicit defaults are traceable; no guarantee that default is ideal for each guest |
| Two guests with same message IDs | PARTIAL | Unit isolation check; full backend concurrent integration gate remains |
| DST / home→hotel | PARTIAL | 32 synthetic cases + Stage 1 DST, no all-horizons oracle |
| Source quote semantics | NOT TESTED | Factual verification beyond substrings and trusted catalog |
| Persistence after restart | NOT TESTED | Stage 6 design, no official session reattach |

No personal data from starter ZIP, external organizer credentials or raw user histories are copied to this report.


---

## Stage 2 completion: evidence → preferences → actual commands

**Source under test:** `c7cb43b1f89e6fb283ddc7cd294ab18f2635eba1`. Local tests use an explicit `EvidenceModel` double; quote integrity and source priority are evaluated by real resolver code, but a fake model is **not** credited with understanding unseen language.

| Tested condition | Code / oracle | Expected and observed behavior | Status |
|---|---|---|---|
| Profile cool vs hotel warm | `test_personalization_scenarios.py` + `build_scenario` | Structured profile retains cool, night climate 17.5 °C | PASS local |
| Profile warm vs newer hotel cool | same | Structured profile precedence retained, night climate 21.5 °C | PASS per documented current policy; product arbitration remains PARTIAL |
| Old hotel warm, newer hotel cool (no profile override) | same | Latest supported hotel behavior sets 17.5 °C | PASS |
| Old hotel cool, newer hotel warm | same | Latest supported behavior sets 21.5 °C | PASS |
| One-off temporary 16 °C request | same | Does **not** become permanent night preference | PASS |
| Disliked sharp alarm | same | Profile dislike with source evidence yields light-only alarm, not fabricated diagnosis | PASS |
| No home/yesterday facts | same | Explicit defaults, safe refusal, no action POST | PASS |
| `like_home` and `like_yesterday` with evidence | Real `Solution.prepare` and `Solution.message` over MockTransport | Confirmed climate 18 °C and light 33 %, no unrelated field changes | PASS local |
| Edit same source ID/timestamp | `test_preparation_explanations.py`, `test_personalization_scenarios.py` | Cache invalidates; next planned night temperature changes 21.5→17.5 °C | PASS |
| Edit user profile | `test_preparation_explanations.py` | Cache key invalidates even if source IDs/timestamps unchanged | PASS |
| Two guests with identical event IDs | `test_personalization_scenarios.py` | Resolves separately, no cross-guest note text | PASS local |
| Simultaneous separate guest sessions | `test_simulator_full_state.py` | Distinct preferences and isolated final real simulator snapshots | PASS local |
| Six-device explanations | `backend/explanations.py` + Stage 2 Python/browser checks | Safe source categories; no raw quotes/IDs, `planned` vs `warning`, no fabricated `confirmed` label | PASS Python; browser gate pending |
| Timezone/DST | Stage 1 UTC and Stage 2 golden/synthetic | Local clocks validated; impossible sunrise explicitly warned | PASS measured cases; R6 always PARTIAL when infeasible |

### Remaining distinctions

- The **current source precedence policy** is explicit profile temperature/tracks before extracted history for the same key. This is deterministic and tested, but not a guarantee that an old profile always outranks more recent observed hotel behavior in production.
- A verified exact quote proves attribution, not truth or general semantic accuracy. Natural-language conflicts/negations not represented by structured evidence remain Stage 3.
- Guest preference caches and action journals are in memory; restart/multiworker durability remains Stage 6.
- A scheduled scene is not a confirmed device state; only a GET-verified snapshot can be shown as actual.

**Retrospective RED:** initial Stage 2 prior key used only evidence source IDs/timestamps and missed edits. That baseline has no separately archived RED run; no fabricated RED proof is claimed. The new regression checks invalidation on changed data after a successful cache read.
