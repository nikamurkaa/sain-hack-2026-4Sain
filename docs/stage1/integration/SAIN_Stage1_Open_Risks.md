# SAIN Stage 1 — Open Risks and Residual Limitations

Date: 2026-11-22 · [Integrated Draft PR #20](https://github.com/nikamurkaa/sain-hack-2026-4Sain/pull/20).

| Risk ID | Severity | Remaining issue | Evidence / impact | Gate / owner |
|---|---|---|---|---|
| S-002/S-024 | HIGH / External & Stage 6 | In-memory ClientSession/Room operations are lost on backend restart; no durable synthetic room snapshots or audit log | Old token invalid, new REHEARSAL session is fresh, not recovered | Stage 6 SQLite WAL/state restore plan, local-only authorization/retention; official upstream blocked on documented session lookup |
| S-003-IMPOSSIBLE | MEDIUM / policy | Check-in <15 real minutes before wake cannot satisfy legal R6 light/curtains window | No event is backdated; API scenario is not explicitly labeled unsatisfiable | Constraint policy/design review, don't count as compliant |
| S-004-LONG | LOW | Extreme time horizons and future tzdata law changes not comprehensively tested | Tested Berlin/NY folds and gaps; local timezone database external dependency | Future tzdata update regression |
| S-008-UPSTREAM | HIGH | Upstream POST/action remains non-atomic and can have unobservable effects | Full-state reconciliation proves observed values only, no remote event receipt | Documented upstream event log or explicitly local authoritative simulator |
| S-008-RESTART | HIGH | In-memory bounded journal capacity and restart invalidate replay protection | Fail-closed at 100 operations; API sessions similarly bounded | Stage 6 persistent idempotency key namespace and event journaling |
| S-009-HYPOTHESIS | MEDIUM | Actual organizer-side duplicate creation on timeout not observed | Fault injection proves risk in *client retry logic*, not proof upstream creates duplicate | Only authorized API contract/replay testing |
| S-010-FUTURE | LOW | No authorized display_name source in official schema; Unicode future UI contract not designed | Neutral titles used, no fabricated name | New data schema + privacy signoff, not Stage 1 |
| S-014-HISTORY | HIGH | No full removed Git blob/other branch/artifact secret audit; candidate scanner is limited to current tracked tree | Heuristics cannot prove absence of secrets or token validity | Independent secrets/rotation review before sharing external artifacts |
| S-014-DEPENDENCIES | MEDIUM | Advisory databases are point-in-time, transitive graph subject to future changes | pip-audit and npm audit in CI, does not prove zero undisclosed vulnerabilities | Continuous scans/advisory review in Stage 6 |
| S-023-IP | HIGH/EXTERNAL | Post-hackathon SAIN branding, visual assets, starter kit and API rights not confirmed | EXTERNAL_APPROVALS.md documents missing permissions | Written approval or replacement before expert distribution |
| WINDOW-NATIVE | MEDIUM | Linux runner ZIP built, native Windows START/STOP not tested | ZIP integrity/checksum != Windows executable acceptance | Independent native Windows QA |
| LIVE-MODEL | MEDIUM | Offline ScriptedModel/FakeLLM and fake STT are not production model quality | 19 scripted intents/10/60 are bounded deterministic tests | Authorized blind benchmark later, not Stage 1 |
| INTEGRATION-CI | BLOCKER if failing | All CI required at **single exact** final PR SHA | Older PR/#20 SHA runs cannot be mixed | Reviewer must verify final PR HEAD/backend/frontend/Windows outcomes |
| REVIEW | BLOCKER for merge | No independent review or user merge approval yet | PR remains Draft, main unmodified | Explicit owner authorization only after review |

## Operational controls

Never perform unsafe retries of creating POST or partial operations when outcome is not verified. Never surface "Готово" for partial or unknown results. Do not treat planned events as actual state. Do not persist bearer tokens, service keys, private ZIPs or raw audio. Do not silently use organizer infrastructure for post-event demonstrations. Historic tag `v1.0.0-hackathon` remains immutable.

These risks are disclosed rather than marked fixed simply because a unit test or offline CI passed.
