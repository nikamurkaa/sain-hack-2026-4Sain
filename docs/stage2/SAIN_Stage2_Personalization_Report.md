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
- Added tests for edited notes, edited profile, cross-guest isolation, missing vs configured preferences and unrealizable dawn.
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
