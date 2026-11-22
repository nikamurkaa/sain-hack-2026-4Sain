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
| R1 | Light 10–30% / ≤2700 K during 60m pre-bed | Existing sleep audit + Stage 1 regression + 24 golden overnights + 24 golden Stage 2 overnights | PARTIAL |
| R2 | Night brightness 0, curtains ≤10 | Existing sleep audit + Stage 1 regression | PARTIAL |
| R3 | 17–18/19–20/21–22 °C based on preferences | Existing sleep audit + 24 golden Stage 2 overnights | PARTIAL |
| R4 | Preferred track, volume 1–30, timer ≤45 or off | Existing sleep audit + Stage 2 synthetic | PARTIAL |
| R5 | Target wake, gentle alarm in light mode | Existing sleep audit + Stage 1 regression | PARTIAL |
| R6 | 3 light rises OR curtains during pre-wake 15–30m | Stage 1 no-backdate + new explicit warning | PARTIAL; impossible late arrival disclosed |
| R7 | DND from bedtime to wake | Existing sleep audit + 24 golden overnights | PARTIAL |
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


---

## Targeted hardening evidence at code snapshot `c7cb43b1f89e6fb283ddc7cd294ab18f2635eba1`

This supplements the 19-family table above rather than changing the meaning of an overall official-compliance result. On a fixed local scripted category input, `test_simulator_full_state.py` sends requests through real FastAPI and a local MockSimulator, then compares **every field of all six devices** to an independently handwritten expected snapshot. It verifies the `done/refused` class and counts actual simulator POSTs. Negative cases must leave all fields untouched. For `like_home`/`like_yesterday`, the missing-data cases correctly refuse, while `test_personalization_scenarios.py` separately proves successful real simulator effects when verifiable history exists.

| Requirement / ID | Executable evidence | Code | Local structural/action status | Overall official status |
|---|---|---|---|---|
| 1 brighter | 19-category full-state test index 0 | `backend/commands.py` | PASS | PARTIAL — real NLU unmeasured |
| 2 dimmer | index 1 | same | PASS | PARTIAL |
| 3 warmer | index 2 | same | PASS | PARTIAL |
| 4 cooler | index 3 | same | PASS | PARTIAL |
| 5 all_off | index 4 | same | PASS | PARTIAL |
| 6 sound_on | index 5, catalog track | same | PASS | PARTIAL |
| 7 quieter | index 6 | same | PASS | PARTIAL |
| 8 curtains | index 7, boundary tests | same | PASS | PARTIAL |
| 9 alarm_set | index 8 | same | PASS | PARTIAL |
| 10 alarm_shift | index 9 | same | PASS | PARTIAL |
| 11 alarm_cancel | index 10 | same | PASS | PARTIAL |
| 12 going_to_bed | index 11 and 5-step sequence | same | PASS | PARTIAL |
| 13 woke_up | index 12 | same | PASS | PARTIAL |
| 14 like_yesterday | index 13 refusal + evidence-backed positive simulator action | `backend/preferences.py`, `commands.py` | PASS tested conditions | PARTIAL |
| 15 do_not_disturb | index 14 | `commands.py` | PASS | PARTIAL |
| 16 like_home | index 15 refusal + evidence-backed positive simulator action | `preferences.py`, `commands.py` | PASS tested conditions | PARTIAL |
| 17 out_of_scope | index 16, zero POST | `commands.py` | PASS | PARTIAL |
| 18 invalid_value | index 17, boundary tests | `commands.py` | PASS | PARTIAL |
| 19 medical | index 18, zero POST | `commands.py` | PASS | PARTIAL |

| Rules / systems | Independent test | Local result and qualification |
|---|---|---|
| R1 | 24 golden overnights + independent sleep audit | PASS for 24 valid patterns |
| R2 | Same + offline 10/60 | PASS for tested valid stays |
| R3 | Same + profile/history change scenarios | PASS within test-extractor model |
| R4 | Golden with and without favorite sound | PASS |
| R5 | Golden with light and both modes | PASS |
| R6 | Golden dawn + specific impossible late-check-in assertion | PASS where feasible; **PARTIAL** globally, no invented events before check-in |
| R7 | Golden DND through sleep, manual bed override | PASS for tested schedules |
| R8 | Two manually resolved home time-zone golden bedtimes + 32 synthetic zone combinations + DST tests | PASS for tested timezones/horizons |
| Six systems: light/climate/curtains/sound/alarm/DND | `test_simulator_full_state.py` GET after every action, all fields compared including unchanged | PASS local full-state and no-extra-change gate |
| Uncertain/partial/fault actions | `test_fault_injection_gate.py`, Stage 1 cancellation/temporal tests | PASS local; upstream real-world atomicity NOT TESTED |
| Prepared rationale | `backend/explanations.py` and browser stage2-explanations test | PASS in Python; browser check requires final successful E2E |
| Model language-generalization | Never supplied hidden input to real model | NOT TESTED (Stage 3) |

No evidence above proves official SAIN hidden-score accuracy or generalized Russian NLU.
