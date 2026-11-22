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
