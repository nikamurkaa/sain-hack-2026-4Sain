# SAIN Stage 1 — Implementation Report

Date: 2026-11-22 · Team 4Sain · Stage: FOUNDATION & CORRECTNESS
**VERDICT: PARTIAL (do not merge).** This is a reproducible engineering implementation record, not a readiness certificate.
Original main: 2820222613c4ea4544b715435aeba59988470783; initial main CI [45016610161](https://github.com/nikamurkaa/sain-hack-2026-4Sain/actions/runs/45016610161) succeeded. Each branch was created independently from that SHA. No production deploy, original organizer token, official /run, force push, main merge, or external handoff was performed.

## 1. Change ledger and root causes

| ID | Draft PR | Root cause | Implemented change | Status |
|---|---|---|---|---|
| S-003 | [#14](https://github.com/nikamurkaa/sain-hack-2026-4Sain/pull/14) | Dawn steps scheduled only at fixed -30/-23/-16; first step clipped/dropped if after check-in | If all 3 legal dawn steps fit, retain existing light profile; else use an R6-authorized curtain opening at wake-15, only when within the stay | FIXED in legal reachable cases; impossible <15m clearly documented |
| S-004 | [#15](https://github.com/nikamurkaa/sain-hack-2026-4Sain/pull/15) | Client derived all future offsets from check-in; DST shift gave impossible local timestamps | Timezone-aware per-instant frontend conversion via Intl IANA, backend IANA wall-clock/offset validation, explicit zone parameter from stay | FIXED under tested Berlin/NY/Moscow boundaries |
| S-008 | [#17](https://github.com/nikamurkaa/sain-hack-2026-4Sain/pull/17) | Multi-device POSTs non-atomic; no recorded confirmation of completed substeps on later failures | Ordered operation plan fingerprint, opaque operation ID, bounded journal, full-snapshot reconciliation per step, distinct failed/partial/uncertain/conflict results | PARTIAL: local safe semantics; not durable, not atomic |
| S-009 | [#16](https://github.com/nikamurkaa/sain-hack-2026-4Sain/pull/16) | Room.create used retry=True on side-effecting POST; transport retried on 503/timeouts | One POST for session creation, no unsafe retry on non-GET/HEAD; safe fail-closed uncertain result; corrected unsafe golden test | Local unsafe retry FIXED; actual upstream duplication remains HYPOTHESIS |
| S-010 | [#18](https://github.com/nikamurkaa/sain-hack-2026-4Sain/pull/18) | Official strict Case2 user data has no display_name; virtual screen retained Figma placeholder “Алина,” | Neutral “Ваш номер” heading, no inferred or invented guest name; Playwright with real offline API | FIXED for source-compatible guest identity |
| S-002/S-024 | [Architecture ADR](SAIN_Stage1_Architecture_Decisions.md) | app.state and session/history idempotency are transient; no durable event log | Scoped in-memory operation journal + minimal SQLite WAL/migrations schema and explicit non-persistence/restart decision | PARTIAL/BLOCKED: no authorized upstream reattachment or real guest-retention contract |
| S-014 | [Security section](#4-security-and-assets-review-s-014) | Secrets and resource handling not independently accepted | Reviewed public history filenames, tracked tree, manifests, CI and packaging; no secret values inspected or copied | PARTIAL: not comprehensive object/content/dependency scan |
| S-023 | [EXTERNAL_APPROVALS](../../EXTERNAL_APPROVALS.md) | Brand, customer assets, post-event API, team and data rights unverified | Recorded every external approval gap and prohibited use | BLOCKED externally; never automatically marked solved |

## 2. Red → green evidence for original defects

**S-003**: new independent 0–31-minute parameterized tests originally failed [at red SHA 306214d5](https://github.com/nikamurkaa/sain-hack-2026-4Sain/commit/306214d5edb9c436d3a1e53f28852ae1b85d7cd7) ([CI red](https://github.com/nikamurkaa/sain-hack-2026-4Sain/actions/runs/45021236288)); later [fix SHA 1474dd26](https://github.com/nikamurkaa/sain-hack-2026-4Sain/commit/1474dd264995dbab2abc76e3f42488d3119fa538) passed. Example: check-in 06:35, wake 07:00 Moscow now opens curtains at 06:45, in legal R6 window, without inventing three past light events.

**S-004**: new JS timezone tests first failed against fixed-offset logic ([red commit](https://github.com/nikamurkaa/sain-hack-2026-4Sain/commit/db2ca3dc948840eb9ab344e1d8e8b2aa67421705)); fixed UTC-offset validation and IANA formatting. A later test *fixture* correction moved the stay end from morning into afternoon so an actual end-of-stay event cannot override the expected generated 06:00 preview; the DST oracle and its intent were not weakened. Backend added nonexistent/ambiguous local clock checks for spring/fall, Moscow, Berlin, New York. [Green backend](https://github.com/nikamurkaa/sain-hack-2026-4Sain/actions/runs/45021820204), [green browser](https://github.com/nikamurkaa/sain-hack-2026-4Sain/actions/runs/45021820137).

**S-008**: first fault-injection tests failed for missing operation-status interface ([red commit](https://github.com/nikamurkaa/sain-hack-2026-4Sain/commit/95e60808fe2a9bc9d66ad81fd65388492a91e09a), [red CI](https://github.com/nikamurkaa/sain-hack-2026-4Sain/actions/runs/45021435357)). Green tests check failed first/middle step, lost reply, state GET timeout, concurrent drift, replay and reconciliation. The exception response now preserves safe metadata across repeated client idempotency keys without declaring an unconfirmed action “Готово”. [Green backend at SHA ed86a7ca](https://github.com/nikamurkaa/sain-hack-2026-4Sain/actions/runs/45022188976); note an additional fault-test commit may supersede this exact SHA; the PR index and GitHub CI are authoritative.

**S-009**: first test proved the local retry branch can send two creation POSTs after a lost first response ([red SHA](https://github.com/nikamurkaa/sain-hack-2026-4Sain/commit/3d0c7ac97e604c1f922f9a700d2a0302c1ce34ef), [red CI](https://github.com/nikamurkaa/sain-hack-2026-4Sain/actions/runs/45021242085)). A pre-existing test incorrectly required three attempts after HTTP 503. Since a 503 after a mutating operation does not establish that nothing was created, this was intentionally corrected, with comment and explicit 59/60 isolated result rather than fabricated session. **That injected failure is not a normal successful 10/60 run**; the standard offline 10/60 remains fully green. [Green backend](https://github.com/nikamurkaa/sain-hack-2026-4Sain/actions/runs/45022191988).

**S-010**: original React virtual screen left a literal Figma guest name, even when the API carries none. Playwright against actual local API failed on missing neutral heading ([red run](https://github.com/nikamurkaa/sain-hack-2026-4Sain/actions/runs/45021860073)); after fix [browser CI succeeded](https://github.com/nikamurkaa/sain-hack-2026-4Sain/actions/runs/45021875785).

## 3. Cross-stack, regression and compatibility

Each PR's backend workflow runs pytest and scripts.check_offline twice (including 1 CPU/512 MiB), using MockTransport, an independently scripted model, 10 synthetic stays, 60 requests and direct comparison of simulator snapshots. All 19 intent classes are covered in synthetic scripted tests; no real-world language-model accuracy is asserted.

Python success counts: S-003 250, S-004 227, S-008 219 on the previous SHA before added tests, S-009 216, S-010 215. All counts are branch-local, **not additive**. Base standard fixture shows 10 stays/60 requests, empty incorrect_requests and failed_rules, zero extra changes, and schema-compliant /run. The browser workflow checks npm unit, TS, production Vite build, actual local backend via REHEARSAL, Chromium and Firefox Playwright. The frontend.yml PR paths were widened within backend-oriented Draft PRs so backend changes trigger browser testing. Final/dev read-only protections were not bypassed.

**Important integration limit:** separate independently green branches are not proof of compatibility once all changes are combined. A separate unmerged integration candidate and full CI suite at its exact SHA are required before any merging request.

Backward compatibility by PR: #14 emits only documented schedule device steps; #15 keeps offset-encoded wire timestamps and introduces no new mandatory API field (hotel_timezone was already in Stay); #17 keeps successful message response shape and only adds safe metadata to error body; #16 intentionally reduces risky retry behavior and may return fewer entries after 503 instead of creating unknown duplicate sessions; #18 uses neutral titles with unchanged official user/API schema.

## 4. Security and assets review (S-014)

**Performed:** GitHub default branch main checked at fixed SHA; public tracked tree and 80 visible main-branch commit diffs checked for *suspicious filenames* (including credential extensions and organizer ZIP). Across these 80 revisions, suspicious filename hits were only the credential-free template .env.example. No private starter kit/key file name was observed in this **specific path-level scan**. Current .gitignore excludes typical secrets, ZIPs and local runtime paths. Python dependencies are version pinned in requirements files; npm has a lockfile used by npm ci. CI workflow permissions use contents: read and backend offline suite blocks outgoing network. Frontend proxy and Windows packaging inspect/limit browser token placement and packaged tracked files. Font license notices for Inter, Manrope, Unbounded are present.

**Not performed:** full raw Git object/patch-content secret scan, branch/ref/release/artifact scan, dependency vulnerability advisory lookup, local developer PC credential scan, original secret verification/rotation, detailed IP/license audit for images. The private starter ZIP was not copied or disclosed; no key values printed. No claim that secrets are absent or that a possible exposed key has been rotated.

**Security posture:** S-014 PARTIAL; S-023 requires signed/written external confirmation. EXTERNAL_APPROVALS.md is a dedicated register, not a license.

## 5. Changes not made

- main remained unchanged and tagged historical versions were not removed.
- No official production/dev stand, /run, external token, live LLM/STT or physical hardware used.
- No migration to SQLite/PostgreSQL, no real API reattachment, no broad refactor or redesign.
- No change to official final read-only rules, user names are not invented.
- No formal expert transfer, no legal approval presumed.

## 6. Delivery and rollback

Every numbered PR is Draft and begins from independently confirmed main. Rollback is to close the Draft PR or revert its commits on the feature branch before integration; do not reset or force push. For incident recovery, first stop writes and reconcile room state. Reverting #17 only removes local status improvements; it does NOT make the underlying upstream operation atomic.

After independent review, prepare an unmerged integration branch and run all Python, TypeScript, Chromium, Firefox, full offline 10/60, failure/restart tests and screenshot inspections on one exact SHA, then request owner approval. Without that evidence, **Stage 1 remains PARTIAL.**

Supporting documents: [Regression Matrix](SAIN_Stage1_Regression_Matrix.md), [Architecture Decisions](SAIN_Stage1_Architecture_Decisions.md), [Remaining Risks](SAIN_Stage1_Remaining_Risks.md), [PR Index](SAIN_Stage1_PR_Index.md), [External Approvals](../../EXTERNAL_APPROVALS.md).
