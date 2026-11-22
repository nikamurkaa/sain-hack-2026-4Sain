# Stage 2 — independent benchmark methodology

This benchmark is intentionally **not** a fabricated NLU score.

- **Source:** official SAIN Case 2, §3 (19 intent categories), §4 (simulator contract) and §9.1 (all-state grading and tolerances). The test file was authored independently of the existing 10/60 ScriptedModel.
- **Structured-action oracle:** `tests/stage2/test_action_benchmark.py` passes validated `Intent` objects into `plan_commands` and compares the entire resulting state against an independent expected state. It covers all 19 categories, 10 refusals/conflicts/bounds, five explicit deltas and an unexpected sequence.
- **Synthetic-stay oracles:** `tests/stage2/test_synthetic_journeys.py` generates 32 cross-product combinations of hotel/home time zones, thermal preferences and sound habits, plus explicit DST transitions. It asserts ranges, strict chronological order and valid hotel offsets; it does **not** independently certify all eight sleep rules.
- **Expected response class:** `None` expected delta means refusal without changes; other deltas mean a planned action. Separate simulator integration tests are required to prove upstream confirmation.
- **What is NOT measured:** accuracy of unknown natural-language paraphrases, typos, contextual disambiguation or a live LLM. `ScriptedModel` is not a genuine NLU model; phrase labels in these tests are explanatory only. Real LLM/STT and private held-out evaluation belong to Stage 3; official credentials and the official stand are prohibited.
- **Future blind evaluation:** keep the undisclosed phrase bank outside the public repository and outside prompts used to develop the parser. Freeze source SHA and test harness; report intent top-1, action full-state accuracy, refusal precision, context consistency, latency, and per-category confidence intervals. No invented scores.
- **Limitations:** official hidden online reference is unavailable; successful pytest is local acceptance of structured execution, never proof of organizer evaluation.
