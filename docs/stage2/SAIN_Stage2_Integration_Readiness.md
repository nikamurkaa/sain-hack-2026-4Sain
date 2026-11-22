# SAIN Stage 2 — Integrated Acceptance and Merge Gate

## Boundary
Base main `2ccad73652a20f93eb93e70e466e958cc731d705`. Feature PR #21 head `8d8c5eba26e9b114fd6b1de9abb675a6a9807571`; test PR #22 head `d2a7ed7de1944b41691beeecce3770c1fc6027b2`. This integrated branch contains **both** changes without merging either PR or main. The exact integrated HEAD must be reported after creation; old CI results cannot replace integrated checks.

## Evidence at integrated code SHA `7a3efc7fa52d5a02312db254d75c4e049c783bf0`

| Check | Evidence | Verdict |
|---|---|---|
| Python 3.11 full pytest | [GitHub Actions run 45055542536](https://github.com/nikamurkaa/sain-hack-2026-4Sain/actions/runs/45055542536): **433 passed, 1 warning** | PASS |
| Scripted offline 10/60 (normal + bounded 1 CPU / 512 MiB) | Same Python run: **10 guests, 60 requests, no incorrect requests or R1–R8 audit failures; C=S=x=1.0** | PASS for ScriptedModel only |
| Python pip advisory + tracked-file candidate secret scan | Same Python run: successful job steps | PASS in CI scope only |
| Windows ZIP package & SHA256 | [GitHub Actions run 45055542576](https://github.com/nikamurkaa/sain-hack-2026-4Sain/actions/runs/45055542576) | PASS (Linux-built; native Windows NOT TESTED) |
| React Node/TypeScript/Playwright | [GitHub Actions run 45055542555](https://github.com/nikamurkaa/sain-hack-2026-4Sain/actions/runs/45055542555) | See current GitHub run; not self-certified here |
| Independent real-model unseen phrases | No evaluation run | NOT TESTED |

These results apply to the **code SHA above**. A subsequent documentation commit needs its own exact-head CI before final integration gate.

## Required exact-SHA checks
- [ ] Python 3.11 full pytest and new Stage 2 tests
- [ ] Offline 10/60 under normal and 1 CPU / 512 MiB
- [ ] R1–R8 golden 24-case suite, 32 synthetic stays and DST
- [ ] Six-device complete state and negative cases
- [ ] Multi-guest isolation and failure injection
- [ ] Stage 1 temporal, cancellation and idempotency
- [ ] Python dependency advisory audit and candidate secret checks
- [ ] Node unit, TS, Vite production build and npm high+ audit
- [ ] Chromium and Firefox Playwright with local fake backend
- [ ] Windows ZIP and SHA256 on source HEAD
- [ ] Independent human review of changed code and fault boundary
- [ ] Private unseen-Russian NLU benchmark (not available; Stage 3)
- [ ] Native Windows START/STOP on real Windows hardware (Stage 7)
- [ ] Official stand (PROHIBITED for this task)

## Acceptance decision
**STAGE 2 — NOT READY FOR INDEPENDENT REVIEW.** This is a truthful interim status until exact integrated SHA CI and independent scenario evidence complete. Missing live NLU / context benchmark and impossible R6 intervals also prevent a blanket "full official compliance" statement.

No pull request may merge without new explicit owner permission. Never use official keys, start remote /run, change main or contact SAIN experts.


---

## 2026-11-22 completion/hardening decision gate (supersedes earlier candidate table)

**Base:** `main=2ccad73652a20f93eb93e70e466e958cc731d705`. **Integrated code snapshot:** `c7cb43b1f89e6fb283ddc7cd294ab18f2635eba1`. Repository branches PR #21/#22 remain independent Draft branches, not merged. Exact file blob comparisons of latest branch heads confirm **9/9 + 4/4 files in PR #23**, including 24 R1–R8 golden nights.

### Chromium CI incident and independent reproduction
1. [Original failing Chromium job, attempt 1](https://github.com/nikamurkaa/sain-hack-2026-4Sain/actions/runs/45055737867), source `53d7546d`: 46 passed, one 45-s test timeout (`screens.spec.ts:175`). [Artifact 14766964369](https://github.com/nikamurkaa/sain-hack-2026-4Sain/actions/runs/45055737867/artifacts/14766964369): screenshots through #28, no #29; error context stuck at final chat view. Underlying product bug not proven.
2. **RED→GREEN nuance:** rerunning **unchanged source** in attempt 2 succeeded. Thus the evidence supports a timing-sensitive test failure, *not* deterministic proof of a fixed production bug.
3. Commit `d65c09e5` split one monolithic 45-s test into three independent journeys with unchanged assertions and screenshots. [Both Chromium and Firefox succeeded, 49 each](https://github.com/nikamurkaa/sain-hack-2026-4Sain/actions/runs/45061740676). No blanket timeout increase, arbitrary sleep, skipped test or disabled assertion.
4. The `No response returned` stack traces came from FastAPI/Starlette request middleware around active client cancellation; their timing does not prove they caused the test timeout. No speculative production middleware patch was introduced.
5. Separate regression **RED** at `eb8491de`: newly synthesized events lacked two required official schema fields, causing 1 failure / 475 pass. **GREEN** after `c69b29ac`: [476 passed](https://github.com/nikamurkaa/sain-hack-2026-4Sain/actions/runs/45062162529), event fields restored without relaxing schema.

### Functional Stage 2 gate

| Requirement | Evidence | Status with local deterministic tests | Qualification |
|---|---|---|---|
| 19 categories × full six-device state, response class and no extra POST | `test_simulator_full_state.py`, 19 FastAPI cases | PASS | Scripted model supplies already known category; NLU still untested |
| Device bound extremes | Same, 12 endpoint boundary cases | PASS | Six specified field families; not all possible catalog combinations |
| Stateful five-command sequence | Same | PASS | Model understands only scripted fixture phrases |
| Profile conflicts, source staleness, negative/temporary, home/yesterday, defaults, identical IDs | `test_personalization_scenarios.py` | PASS | Test extractor, not real semantic conflict reasoning |
| Concurrent distinct user sessions | `test_simulator_full_state.py` | PASS | Single process and local simulator |
| Partial / uncertain / cancelled / 422 / duplicate / past writes | `test_fault_injection_gate.py` plus full Stage 1 regressions | PASS | Real POST and GET in loopback; not official API |
| R1–R8, 24 golden nights, 32 synthetic, DST | `test_sleep_criteria_matrix.py`, `test_synthetic_journeys.py` | PASS in valid windows | Impossible <15-minute R6 stays produce `warning`; not counted as compliant |
| Python 3.11 suite | [Run 45062162529](https://github.com/nikamurkaa/sain-hack-2026-4Sain/actions/runs/45062162529) | PASS — 476 tests | Earlier exact code SHA `c69b29ac`; final doc SHA must rerun |
| Offline 10/60 normal and 1 CPU/512 MiB | Same Python run | PASS | ScriptedModel only, never official score |
| React Node/TS/Vite/npm + Chromium/Firefox + stage2 rationale | Final PR #23 workflow | PENDING exact-head conclusion | Full job must SUCCESS |
| Windows ZIP and checksum | Final PR #23 workflow | PENDING exact-head conclusion | No native Windows run |

### Final signoff rule

Only if **all three** workflow runs associated with the final integration HEAD are **SUCCESS**, and every functional scope row above passes, the PR body may state **STAGE 2 — READY FOR TARGETED INDEPENDENT REVIEW**. This phrase means a reviewer can examine the tested single-process local solution; it **does not** authorize merge or imply general NLU, official judge score, official simulator, Windows-native certification, persistent recovery, commercial/IP permission or production readiness.

If any exact-head gate fails or is absent, verdict is **STAGE 2 — BLOCKED** and the failing run ID/issue must be recorded in PR #23. Stage 3 real NLU/LLM/STT and the private 86-item holdout remain excluded and unshared. No official credentials, stand operations, branch deletion, merge or expert contact were performed.
