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


---

## 2026-11-22: Independent MR-001–MR-004 remediation (PR #20)

This section supersedes any earlier *merge-readiness claim* in the original Stage 1 document; pre-remediation CI does not establish acceptance of the new HEAD. Full issue-by-issue proof, reproducible tests, red-green SHA links, scope and reviewer questions: [SAIN_Stage1_Merge_Review_Remediation.md](SAIN_Stage1_Merge_Review_Remediation.md).

| Additional risk | Severity | Residual boundary / independent review task |
|---|---|---|
| MR-001 malformed external error bodies | LOW | Unknown/malformed JSON falls back to ordinary safe ApiError, never to fabricated confirmed_devices. Verify external clients still handle non-action HTTP 409 by code. |
| MR-001 visual presentation | LOW | Semantic action overlay works in original SAIN mobile/desktop theme; manual physical-device accessibility/contrast review is still separate. Four Playwright PNG screenshots per CI run (Chromium/Firefox, mobile/desktop) are captured in the browser artifact. |
| MR-001 GET after error | MEDIUM | If state GET fails, mark stale/unknown and require GET verification before new action; a successful GET proves current observed snapshot, *not* external operation receipt or atomic upstream mutation. |
| MR-002 ambiguous alarm local time | LOW | HH:MM lacks fold offset, so reject ambiguity with 422 rather than silently choosing an occurrence. Valid explicit-offset timestamps remain subject to IANA backend validation. |
| MR-003 habitual bedtime policy | LOW | No input offset in profile: choose earliest valid repeated time; gap is shifted forward to first real local time. Human confirmation of this policy may be needed if product scope expands beyond synthetic R1–R8. |
| MR-004 CI provenance | LOW | Checkout pinned and SHA asserted per job; GitHub Actions jobs are still GitHub-hosted, public advisory data point-in-time, actions version tags not immutable SHA-pinned. |
| Single-worker / restart boundary | HIGH for distributed deployment, accepted local-only | One Room owner per remote session; per-object asyncio lock and in-memory journal are not shared between processes. On restart guest tokens and operation journal expire; start fresh REHEARSAL, no official reattach. Durable authorized local persistence deferred to Stage 6. |

The standalone [remediation report](SAIN_Stage1_Merge_Review_Remediation.md) must be reviewed alongside the prior integration reports; it does not independently close S-002/S-024 or IP/licensing issues.


---

## TEMPORAL FINAL GATE — MR-NEW-01/02/03 (2026-11-22)

> **Supersedes earlier review-ready claims based on `fb3b082...`.** The independent second review found a new P1 temporal inconsistency; the older 305/28-each green runs are **not** acceptance of the new code. Final disposition requires three new SUCCESS workflows whose jobs checked out the **same last PR HEAD**, independent signoff, and a separate owner merge decision. Full technical explanation: [SAIN_Stage1_Temporal_Recovery_Remediation.md](SAIN_Stage1_Temporal_Recovery_Remediation.md).

| MR-NEW-01 residual external semantics | HIGH for production, accepted single-process local only | GET reconciliation proves observed actual device state at the attempted instant, NOT remote transaction receipt, unobservable side effects or exactly-once; no authorized upstream session reattach exists. Stage 6 persistence alone cannot resolve organizer receipt gaps. |
| MR-NEW-01 crash | HIGH if session survives restart | In-memory issue journal, floor and tokens vanish on process restart; always fresh synthetic session, no silent continuation of old upstream identity. |
| MR-NEW-02 mobile affordance | LOW after code/test | Semantically and visually disabled while unresolved; physical touch usability still awaits manual device QA. |
| MR-NEW-03 accessibility hardware | LOW / follow-up | Browser viewport/zoom/keyboard/focus/screenshot coverage complete in local synthetic E2E; actual mobile OS keyboard, tactile hit target and screen-reader audit not performed. Do not claim WCAG AA or native UI QA. |
| Windows package vs source paths | Resolved test oracle | Source uses `windows/`, distribution intentionally flattens launch scripts beside START/STOP; package file layout isn't the source tree. Strict test accepts either with BUILD_INFO evidence; no duplicate files added. |

**No external-use authorization:** this local Stage 1 evidence does not authorize distribution of SAIN branding, host assets, organizer token use, production release or claims of durable multi-worker correctness. A fresh independent review and owner decision remain pending.
