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

**No inferred language-model accuracy, F1, official score or organizer result.** An offline fake model cannot generalize, and matching a scripted fixture does not prove understanding. Phrase labels in tests describe expected category only; production parser is not trained or adjusted on them.

## Proper Stage 3 acceptance criteria
Freeze hidden paraphrases separately from public code and tuning. Measure by intent and final room-state exactness, refusal precision, multi-turn context, compound commands, all six devices, timeout/errors and privacy isolation with real authorized LLM + local simulator. Report version, seed, total N, real model ID, thresholds and confidence intervals. Do not call organizer proxy or publish private credentials.
