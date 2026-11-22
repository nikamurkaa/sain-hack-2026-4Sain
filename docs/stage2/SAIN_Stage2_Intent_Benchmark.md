# SAIN Stage 2 — Independent Intent/Action Benchmark

## Measured object
The primary benchmark in PR #22 evaluates **structured intent → command planning → entire expected state**. It is independent of the existing hardcoded `tests/offline_cases.py` 10/60 phrases and verifies unchanged values, refusals and direction of changes. It is **not** independent NLU.

| Dataset | Definition | Count | Result |
|---|---|---:|---|
| Official categories | One independently written oracle row per category (§3) | 19 | PARTIAL until integrated SHA CI |
| Refusal / ambiguous / bounds | Negative, unsupported, clarification and out-of-range | 10 | PARTIAL until CI |
| Explicit numeric deltas | Warm/cool/brighter/dimmer/quieter | 5 | PARTIAL until CI |
| Unexpected sequence | Five sequential structured commands | 1 | PARTIAL until CI |
| Independent R1–R8 golden oracles | 2 home timezones × 3 temperatures × 2 sound habits × 2 alarm modes, plus an intentionally corrupted scenario | 24 + 1 negative | PARTIAL until CI |
| Synthetic personalization/timezone | Cross product of 4 hotel zones × 2 home zones × 2 thermal classes × 2 sound habits | 32 | PARTIAL until CI |
| DST | Berlin forward/backward transitions | 2 | PARTIAL until CI |
| Independent unseen Russian phrasing | A blinded private set evaluated by real LLM/NLU | 0 executed | NOT TESTED |
| Contextual multi-turn inference | Unknown phrases interpreted by a genuine model | 0 executed | NOT TESTED |
| Current simulator full-state actions | Actual Room execute using real upstream | 0 new official runs | NOT TESTED |

At integrated code SHA `7a3efc7fa52d5a02312db254d75c4e049c783bf0`, [Python CI](https://github.com/nikamurkaa/sain-hack-2026-4Sain/actions/runs/45055542536) completed **433 passed** including all Stage 2 action/golden oracle tests. The hidden natural-language set comprises 86 prompts stored **outside the public repository**, and has never been executed against a real LLM; it does not enter this score.

**No inferred language-model accuracy, F1, official score or organizer result.** An offline fake model cannot generalize, and matching a scripted fixture does not prove understanding. Phrase labels in tests describe expected category only; production parser is not trained or adjusted on them.

## Proper Stage 3 acceptance criteria
Freeze hidden paraphrases separately from public code and tuning. Measure by intent and final room-state exactness, refusal precision, multi-turn context, compound commands, all six devices, timeout/errors and privacy isolation with real authorized LLM + local simulator. Report version, seed, total N, real model ID, thresholds and confidence intervals. Do not call organizer proxy or publish private credentials.


---

## Post-hardening measurement: source `c7cb43b1f89e6fb283ddc7cd294ab18f2635eba1`

| Test gate | Count / cases | Oracle | Status |
|---|---:|---|---|
| Structured action families | 19 | Handwritten complete six-device expected state | PASS on local Python CI |
| Actual FastAPI + MockSimulator category round trips | 19 | Re-read all six systems; compare `reply.response_class`, full state and upstream POST count | PASS local |
| Explicit device boundaries | 6 device fields × 2 endpoints = 12 cases | Test fixture prestate + handwritten changed field, unchanged-field equality | PASS local |
| Context-sensitive sequence on one live room | 5 consecutive scripted commands | Handwritten expected state after **each** action | PASS local |
| Pre-existing negative ambiguity/boundary tests | 10 + 5 numeric deltas | Structured `Intent` planner, not semantic inference | PASS local |
| Independent R1–R8 golden nights | 24 plus 1 deliberately corrupted scenario | `scripts.sleep_audit` and fixed manually resolved R8 bedtimes | PASS realizable cases |
| Synthetic stays/timezones | 32, plus 2 Berlin DST transitions | Chronology, catalog bounds, valid offsets | PASS scope-limited |
| Preference and fault injection | See personalization/regression reports | Local FastAPI and source-verified synthetic facts | PASS tested paths |
| Blind unseen Russian NLU/STT | **0** in Stage 2 | Real model is intentionally out of scope | NOT TESTED |

Historical offline 10/60 `C=S=x=1.0` is a **ScriptedModel** fixture outcome, never an estimated official score. Current expected states do **not** call the planner to generate the oracle; the input state is read from the simulator and the required effect is fixed by the test. More requests for genuinely unseen language, typos and multi-turn LLM inference belong to Stage 3 only.

[RED test-fixture evidence](https://github.com/nikamurkaa/sain-hack-2026-4Sain/actions/runs/45062027042): 1 failed / 475 passed due to missing official event fields. [GREEN corrected fixture](https://github.com/nikamurkaa/sain-hack-2026-4Sain/actions/runs/45062162529): **476 passed**; source `c69b29ac`. No hidden 86-item benchmark file exists in the public tree.
