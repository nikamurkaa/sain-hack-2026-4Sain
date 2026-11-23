# Stage 3 — real NLU and full-state benchmark

**LIVE NLU ACCURACY: NOT COMPUTABLE.** No successful external model request has been observed in this acceptance cycle. Baseline `main`: `4941f0be9a6531b553aeb50cccc75d4fd2c433e8`.

## Independent probe matrix (not the closed 86-phrase benchmark)
The 19 supported intent classes from the repository:
`brighter`, `dimmer`, `warmer`, `cooler`, `all_off`, `sound_on`, `quieter`, `curtains`, `alarm_set`, `alarm_shift`, `alarm_cancel`, `going_to_bed`, `woke_up`, `like_yesterday`, `do_not_disturb`, `like_home`, `out_of_scope`, `invalid_value`, `medical`.

Suggested independently specified cases (one per class, then add variants):
- «Добавь света» → brighter; «Свет слишком яркий» → dimmer; «Мне холодно» → warmer; «Мне душно» → cooler.
- «Выключи всё» → all_off; «Включи спокойную музыку» → sound_on; «Сделай музыку потише» → quieter; «Закрой шторы» → curtains.
- «Разбуди завтра в полседьмого» → alarm_set (06:30 local, tomorrow); «Перенеси будильник на полчаса позже» → alarm_shift (+30 min); «Отмени будильник» → alarm_cancel.
- «Ложусь спать» → going_to_bed; «Я проснулся» → woke_up; «Сделай как вчера» → like_yesterday; «Включи не беспокоить» → do_not_disturb; «Хочу как дома» → like_home.
- «Закажи такси» → out_of_scope; «Поставь 35 градусов» → invalid_value / refusal (bounded safety); «Что выпить, чтобы уснуть?» → medical / safe refusal.

**Important:** The illustrative natural-language mapping above is a proposed oracle, not verified model output; the organizer's catalog and permitted values take precedence on real data.

## Metrics (three separate gates)
| Metric | Definition | Result |
|---|---|---|
| STRUCTURED CORRECTNESS | Strict `Intent` Pydantic JSON and parameter validation | Implementation present; real-provider metric NOT TESTED |
| REAL NLU ACCURACY | Correct intent/parameters on non-synthetic paraphrases with independence from model output | NOT COMPUTABLE (0 real evaluated samples) |
| FULL-STATE ACTION ACCURACY | All fields of all six devices, response class and preservation of untouched fields vs independently stated oracle | NOT COMPUTABLE (no live model + verified simulator E2E) |

## More adversarial probes
Test Russian typos, relative changes, follow-ups «Ещё немного», ambiguities, local time/DST, negations, multiple independent actions, out-of-range values and prompt injection. The user must not be able to change system instructions or bypass `plan_commands`. Require `done` only after simulator state readback. Refusal must leave every field unchanged.

## Implemented distinction
Stage 3 forces `parse_intent(..., force_model=True)` when `ModelClient` is active, including common phrases that Stage 2 could shortcut. The simulated/offline test model still uses the deterministic shortcut. This is a **code path change**, not measured accuracy.

**Results are withheld until real token-accessible E2E runs are captured with SHA, timestamp, endpoint, latency, actual output class, original expected state and redacted mismatches.**
