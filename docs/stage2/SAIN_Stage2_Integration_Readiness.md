# SAIN Stage 2 — Integrated Acceptance and Merge Gate

## Boundary
Base main `2ccad73652a20f93eb93e70e466e958cc731d705`. Feature PR #21 head `c517764c7d945e6444695b8967eeb26ce013f11d`; test PR #22 head `3fa2f8b396da4e67cb54ce622cf024818564a156`. This integrated branch contains **both** changes without merging either PR or main. The exact integrated HEAD must be reported after creation; old CI results cannot replace integrated checks.

## Required exact-SHA checks
- [ ] Python 3.11 full pytest and new Stage 2 tests
- [ ] Offline 10/60 under normal and 1 CPU / 512 MiB
- [ ] R1–R8 and synthetic DST
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
