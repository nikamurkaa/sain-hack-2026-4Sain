# SAIN Stage 2 — Official Case Compliance Matrix
Official case №2, version 16.11.2026, §§1–10. The 19 categories below are from §3; grading requires the **entire final simulator state** and per-reply class (§9.1), not merely intent detection.

Status legend: PASS = verified at stated scope and exact commit; PARTIAL = bounded local evidence, important conditions unproved; FAIL = verified violation; NOT TESTED = no proof.

| # | Official category | Test basis | Status |
|---:|---|---|---|
| 1 | Brighter | Structured-action complete-state oracle | PARTIAL |
| 2 | Dimmer | Structured-action complete-state oracle | PARTIAL |
| 3 | Warmer | Structured-action complete-state oracle | PARTIAL |
| 4 | Cooler | Structured-action complete-state oracle | PARTIAL |
| 5 | All off | Structured-action complete-state oracle | PARTIAL |
| 6 | Sound on | Structured-action complete-state oracle | PARTIAL |
| 7 | Quieter | Structured-action complete-state oracle | PARTIAL |
| 8 | Curtains open/close | Structured-action complete-state oracle | PARTIAL |
| 9 | Alarm set | Structured-action complete-state oracle | PARTIAL |
| 10 | Alarm shift | Structured-action complete-state oracle | PARTIAL |
| 11 | Alarm cancel | Structured-action complete-state oracle | PARTIAL |
| 12 | Going to bed | Structured-action complete-state oracle | PARTIAL |
| 13 | Woke up | Structured-action complete-state oracle | PARTIAL |
| 14 | Like yesterday | Structured-action complete-state oracle | PARTIAL |
| 15 | DND | Structured-action complete-state oracle | PARTIAL |
| 16 | Like home | Structured-action complete-state oracle | PARTIAL |
| 17 | Out of scope refusal | No-mutation oracle | PARTIAL |
| 18 | Invalid value refusal | No-mutation oracle | PARTIAL |
| 19 | Medical refusal | No-mutation oracle | PARTIAL |

All 19 statuses remain PARTIAL even after test success: the deterministic oracle supplies Intent objects and **does not test unseen Russian utterance classification**.

| Rule/system | Official requirement | Evidence | Status |
|---|---|---|---|
| R1 | Light 10–30% / ≤2700 K during 60m pre-bed | Existing sleep audit + Stage 1 regression | PARTIAL |
| R2 | Night brightness 0, curtains ≤10 | Existing sleep audit + Stage 1 regression | PARTIAL |
| R3 | 17–18/19–20/21–22 °C based on preferences | Existing sleep audit + Stage 2 synthetic | PARTIAL |
| R4 | Preferred track, volume 1–30, timer ≤45 or off | Existing sleep audit + Stage 2 synthetic | PARTIAL |
| R5 | Target wake, gentle alarm in light mode | Existing sleep audit + Stage 1 regression | PARTIAL |
| R6 | 3 light rises OR curtains during pre-wake 15–30m | Stage 1 no-backdate + new explicit warning | PARTIAL; impossible late arrival disclosed |
| R7 | DND from bedtime to wake | Existing sleep audit | PARTIAL |
| R8 | ≥3-hour timezone change capped at 1-hour bedtime adjustment | Stage 1 UTC/DST fixes + Stage 2 property matrix | PARTIAL |
| Light | Current value from GET state, not scheduled preview | `Room.state`, React snapshot | PARTIAL |
| Climate | Current value from GET state | same | PARTIAL |
| Curtains | Current value from GET state | same | PARTIAL |
| Sound | Current value from GET state | same | PARTIAL |
| Alarm | Current value from GET state | same | PARTIAL |
| DND | Current value from GET state | same | PARTIAL |
| Per-user profile, history, source precedence | Factual notes outrank unsupported assertions; never invent data | `PreferenceResolver`, proof of quote existence | PARTIAL — semantic preference correctness not certified |
| Refusal with reason | Out-of-scope, invalid, medical, simulator failures | `commands.py`, `room.py` | PARTIAL |
| API validation, sessions | Separate session per stay/request, official schemas | Stage 1 offline 10/60 | PARTIAL |
| No medical treatment advice | Lifestyle-only wording / decline medication | Deterministic refusal | PARTIAL — external medcheck not run |
| Final UI and actual state | Checkout, planned room, current state, changes/errors | React/Playwright CI | PARTIAL |
| Live LLM / real STT | Stage 3 explicitly deferred | No use of organizer keys | NOT TESTED |
| External final deployment / score | Official stand forbidden | No upstream calls | NOT TESTED |

No 100% official compliance claim is justified by these bounded results.
