# SAIN Stage 1 — Integration Report

**Date:** 2026-11-22 · **Team:** 4Sain · **Scope:** Foundation & Correctness only.
**Main baseline:** `2820222613c4ea4544b715435aeba59988470783`.
**Integration branch:** `integration/stage1-foundation-acceptance` · [Draft PR #20](https://github.com/nikamurkaa/sain-hack-2026-4Sain/pull/20).
**Last pre-documentation code+CI checkpoint:** `b29ad6381bd7ed755e7e18addbe766614907f715`. The **final** integration HEAD is the GitHub PR head and must match the exact GitHub Actions run SHA; this document commit changes its own SHA and cannot self-reference it.
**Boundary:** No merge into main, force push, production deployment, official token, official /run, final read-only bypass, historic tag change, or expert contact.

## 1. Source history and verified ancestry

The integration branch was created directly from the checked baseline main. True two-parent merge commits preserve the complete original PR histories (not a squash, cherry-picked copy, or temporary GitHub merge ref):

| Source | Issue | Original PR HEAD | Integration merge commit |
|---|---|---|---|
| [#14](https://github.com/nikamurkaa/sain-hack-2026-4Sain/pull/14) | S-003 short-stay R6 | 13491b93a014e3550a95f2f6874079c649080340 | af260d217b8b98d01c40f293def3787fe6d485d8 |
| [#15](https://github.com/nikamurkaa/sain-hack-2026-4Sain/pull/15) | S-004 IANA/DST | 6f2f2c6222df9be5d487cc2959e5ce30ce4e125f | 87d4658c7891132b30dbbd3f50612205a27c64a7 |
| [#16](https://github.com/nikamurkaa/sain-hack-2026-4Sain/pull/16) | S-009 session create retry | fb916c1d24e7097026134a74ea62392247120f15 | bcfbaf6f5823e11b0bb72f5603910688522ddff5 |
| [#17](https://github.com/nikamurkaa/sain-hack-2026-4Sain/pull/17) | S-008 partial actions | 44ae58874ddfa42b26f0ca25c9c5681d882fde9b | 5fd47fd851346fef54d71fd304e0be24de12bf0c |
| [#18](https://github.com/nikamurkaa/sain-hack-2026-4Sain/pull/18) | S-010 identity | ad41044caa79242fd6c8be61f8425385c48ffc68 | 9603d30cb9ed3ea329e9e3ff48445ef69026fb5d |
| [#19](https://github.com/nikamurkaa/sain-hack-2026-4Sain/pull/19) | ADR, security, evidence | 1d0500609832c7cfd5bea92a2b0bf24edbe8a153 | dc09c62c9c8d7ccfd19c64589ca76bfaad8f53da |

**Conflicts reviewed manually:** `backend/room.py` (PR #16 vs #17: keep non-retry creating POST AND confirmed-step saga) and `main.py` (PR #15 vs #17: keep hotel_moment validation AND action-error metadata/idempotency). `.github/workflows/frontend.yml` had identical blobs in #14/#16/#17 and was deduplicated, not overwritten. No original PR branches were changed.

## 2. Independent cross-PR review findings & red→green proof

The initial merged tree **passed its old suite** but revealed genuine missing coverage. New integrated tests were committed BEFORE each correction:

| New issue | Red test SHA / CI | Root cause | Corrective commit |
|---|---|---|---|
| INT-001 · idempotent error drops confirmed steps | 4f1ef19a15dabacd649c847875cd48afc3f48deb · [red CI](https://github.com/nikamurkaa/sain-hack-2026-4Sain/actions/runs/45023614995) | main.py rebuilt ActionFailure as a plain ServiceError on HTTP retry; confirmed_devices and operation_id were lost | 709853ad57a724e484c1e89f5d99461f372b1cf9 |
| INT-002 · concurrent distinct commands race | Same red SHA/run | Room.execute lacked per-room serialization; two operations read the same previous state, POSTed both and then falsely reported conflicts | bfa67acce45288a4af1298dcc7e9be1fecca9199 |
| INT-003 · journal evicts an operation ID | Same red SHA/run | On 101st operation the oldest key was deleted, enabling a later duplicate side effect | bfa67acce45288a4af1298dcc7e9be1fecca9199; fail closed with OPERATION_LIMIT |
| INT-004 · scheduler emits DST-invalid device events | b1f34fb6f95cbfaf3086263170a0325167a4aa1b · [red CI](https://github.com/nikamurkaa/sain-hack-2026-4Sain/actions/runs/45023775230) | Fixed-offset timestamp arithmetic crossed spring/fall transition, generating nonexistent/misoffset local event times | fe36cdc5197a1b254e1e0e4c8ef120f3c8fa31b0 |
| INT-005 · replay downgrades confirmed PARTIAL to UNKNOWN | e6e613012b15cb0915943a04933bac30c11bf1bb · [red CI](https://github.com/nikamurkaa/sain-hack-2026-4Sain/actions/runs/45023919917) | Room.operations did not retain a stable sanitized failure classification | c6a8da64807e53129cd471c8cdce55121101f8ea |
| INT-006 · drift status mislabeled | Same red SHA/run | ACTION_CONFLICT was stored as status='uncertain' even though a full-state conflict was observed | c6a8da64807e53129cd471c8cdce55121101f8ea |

The cross-PR regression oracle is `tests/stage1/test_cross_pr_integration_red.py`, which covers a real FastAPI cached-error response and asynchronous concurrent Room operations. The DST oracle is `tests/stage1/test_integrated_dst_scheduler_red.py`, comparing real UTC instants plus date-specific IANA offsets in Moscow, Berlin and New York. All tests remain in the integration candidate. Do **not** modify the red commit history or relax assertions to claim green.

## 3. R6 and DST algorithm evidence

For normal stays there are three ascending dawn steps at 30, 23 and 16 real minutes before wake. When the full three-step window is unavailable and a valid -15m instant remains, opening curtains is the official permitted substitute. At check-in fewer than 15 **real** minutes before wake, no valid R6 event exists; the implementation does not backdate it and **must not claim full R6 satisfaction**. This is a documented constraint-policy limitation, not a green compliance claim.

After integration correction, schedule boundaries and device event ordering use UTC instants; each event is serialized using ZoneInfo(`hotel_timezone`). Spring-forward nonexistent wall-clock times and fall-back stale offsets are never generated for the parameterized cases. Backend API validation rejects mismatched or impossible client-supplied times; frontend previews use Intl IANA at each instant. Future-time GET never writes to confirmed actual state.

## 4. Non-atomic operations and session creation jointly

Room.create performs one side-effecting POST only; the HTTP client rejects unsafe method retries. For action sagas, the **per-room async lock** protects state read→POST→full-state verification. A bounded in-memory journal records fingerprints, operation IDs, sanitized status/errors, full confirmed state and confirmed device IDs. Replays of a successful operation return the recorded state; replays of known partial/conflict retain their original error and confirmed devices; uncertain results never trigger another action POST. Once the journal is full, new commands fail closed, rather than evicting replay protection. API-level idempotent error replay preserves exception metadata. Individual upstream POSTs remain **non-atomic**; no exactly-once or crash durability claim is made.

HTTP 503/lost response from session creation can have an unknown result; no new request is issued without upstream documented reconciliation. Final guest remains read-only and the official /run is untouched. Local REHEARSAL accepts fresh synthesized sessions after restart, **not old token or old operation recovery**.

## 5. Security and IP review

Added CI advisory scans: pinned `pip-audit==2.10.1` against public PyPI advisory data, and `npm audit --audit-level=high` against the locked npm graph. Added a bounded no-network tracked-file secret candidate guard: only reports suspect paths/counts, never secret bytes, and runs in CI. These scans cannot clear historic Git objects, every binary asset, private developer files, credentials' live validity or third-party licenses. React/Vite are built as a client-only SPA; vulnerabilities in server-only React components do not prove this app is affected. See EXTERNAL_APPROVALS.md and the final risk register.

## 6. CI, browser/screenshots and rollback

Backend workflow: full pytest, Python advisory scan, tracked-secret candidate gate, independent two offline /run executions (normal and 1 CPU / 512 MiB). Earlier integrated checkpoint `c6a8da64807e53129cd471c8cdce55121101f8ea` passed **284 Python tests and 10/60, no failed rules/extra changes** ([run 45023991424](https://github.com/nikamurkaa/sain-hack-2026-4Sain/actions/runs/45023991424)); Python advisory scan subsequently passed at `767ce6576e18e246e7bd8b14ebdce7ff07ad2e83` ([run 45024072125](https://github.com/nikamurkaa/sain-hack-2026-4Sain/actions/runs/45024072125)). Final branch HEAD's own checks supersede those historical results.

Frontend workflow installs locked npm packages, audits graph, runs Node unit/TypeScript/Vite build and Chromium + Firefox E2E against actual local REHEARSAL backend, and uploads screenshots. Windows workflow builds/verifies ZIP/checksums on Linux, **not on native Windows**. Final consolidated run URLs and conclusion are recorded on [Draft PR #20](https://github.com/nikamurkaa/sain-hack-2026-4Sain/pull/20), not inferred from individual feature PRs.

Rollback: do NOT merge. For integrated-only defect, revert the matching corrective commit on this integration branch (without force push); keep original PRs unchanged. After future approved merge, revert the merge on main via a normal new PR/commit, re-run all offline/browser security checks and re-validate currently authoritative room state before any write. Unknown external POST outcomes must never be retried blindly.

**Acceptance boundary:** ready for independent technical review only when every required workflow is green on the exact final integration PR HEAD. Durable third-party session reattachment, source licensing and native Windows testing remain separate documented blockers to external production/demo use.


---

## 2026-11-22: Independent MR-001–MR-004 remediation (PR #20)

This section supersedes any earlier *merge-readiness claim* in the original Stage 1 document; pre-remediation CI does not establish acceptance of the new HEAD. Full issue-by-issue proof, reproducible tests, red-green SHA links, scope and reviewer questions: [SAIN_Stage1_Merge_Review_Remediation.md](SAIN_Stage1_Merge_Review_Remediation.md).

**Review source:** the independent read-only merge report with verdict REQUEST CHANGES BEFORE MERGE. No reviewer has yet independently approved these corrections. MR-001, MR-002, MR-003 and MR-004 were addressed in the *same existing integration branch*. Main, historical tag, original PR branches, production APIs and final read-only were not changed.

**Code checkpoint before this documentation change:** `5be7f4c05974b31f8bfc8dd0dae6c091162151f5`. Backend proof [45028432526](https://github.com/nikamurkaa/sain-hack-2026-4Sain/actions/runs/45028432526): 305 pytest passed, two offline 10/60 green, Python dependency advisory scan clean at that point. Frontend Chromium/Firefox, npm audit and the Windows ZIP must be confirmed against the **final post-documentation PR HEAD** separately, using the three run URLs published in the PR body. Do not combine green checks from different SHAs.

**MR-001:** whitelisted typed `ActionApiError` preserves validated operation ID and confirmed device IDs. SAIN-localized partial/uncertain/conflict notice does not display `done` or offer whole-message retry. Real local-only REHEARSAL MockTransport can deterministically fail the second action, lose a response, force a GET failure or create a concurrent state drift. FastAPI TestClient checks idempotent HTTP 409 replay, exact metadata and one upstream action; browser E2E checks response → UI → GET reconciliation, keyboard action, 375×812 and 1440×900. Screenshots are generated in `frontend/evidence/mr001-partial-*.png` and uploaded by `browser-screens` artifact.

**MR-002:** `Refusal` from `_local_alarm` is explicitly converted into stable 422 `INVALID_TIME` and stored against the request idempotency key before any simulator action. Gap/fold for Berlin and New York refuse; valid Moscow/DST-side and next-day cases succeed without altering unrelated devices.

**MR-003:** habitual local bedtime uses first valid fold occurrence (`fold=0`) where input contains no offset; nonexistent spring wall time advances to the first valid future local time. All candidate comparisons, R8 +1/−1h correction and scenario sorting use UTC instants. Independent scheduler tests assert actual device-event UTC ordering.

**MR-004:** backend CI uses `github.event.pull_request.head.sha || github.sha`, explicit non-credential checkout, `git rev-parse HEAD` and fail-on-mismatch. Frontend and Windows preserve their existing exact-head guards. Actions have `contents: read`, no `pull_request_target` secret context.

**Supported topology:** single process, single worker, local in-memory journal; fresh guest session after process restart. No distributed coordination, remote reattachment, upstream exactly-once, SQLite durability or external licensing approval.

**Rollback:** normal non-force revert on the integration branch only, then rerun all exact-head checks; never blindly retry an uncertain POST and never merge main without a fresh independent acceptance.


---

## TEMPORAL FINAL GATE — MR-NEW-01/02/03 (2026-11-22)

> **Supersedes earlier review-ready claims based on `fb3b082...`.** The independent second review found a new P1 temporal inconsistency; the older 305/28-each green runs are **not** acceptance of the new code. Final disposition requires three new SUCCESS workflows whose jobs checked out the **same last PR HEAD**, independent signoff, and a separate owner merge decision. Full technical explanation: [SAIN_Stage1_Temporal_Recovery_Remediation.md](SAIN_Stage1_Temporal_Recovery_Remediation.md).

**MR-NEW-01:** Server now distinguishes last successful `session.at` from the monotonic potentially applied `mutation_floor`. Typed action errors carry trusted `attempted_at` and confirmed devices; GET `/reconciliation?operation_id=` reads **exact T2** with journal cross-check. Default GET T1 or future preview never unlocks T2 action or rewrites newer `last_confirmed`. After successful verification only new explicit write at `next_action_at >= T2` is permitted. No unsafe POST replay.

**MR-NEW-02/03:** Shared `canSubmit`, explicit disabled/aria explanation even with nonempty mobile draft, and in-flow (non-overlapping) alert at 320×568 through desktop; decorative send circle visibly dimmed when unresolved. Existing SAIN Figma room cards and all six devices retained.

**Packaging oracle:** `tests/test_quality_gate_time_ops.py` explicitly distinguishes source `windows/*.ps1` and flattened Windows ZIP root scripts without modifying either package; independent full pytest from flat artifact **311 passed**, 10/60 offline passed. Before this doc update, exact code-only CI evidence: [backend](https://github.com/nikamurkaa/sain-hack-2026-4Sain/actions/runs/45032271808) 311 pytest; [frontend](https://github.com/nikamurkaa/sain-hack-2026-4Sain/actions/runs/45032271827) 41 Chromium + 41 Firefox; [Windows](https://github.com/nikamurkaa/sain-hack-2026-4Sain/actions/runs/45032271793) package. New exact-final-HEAD runs supersede them and are linked from PR #20.


---

## MR-NEW-04 — cancellation safety supersedes earlier merge-readiness claims (2026-11-22)

**Independent reviewer verdict on old SHA `def405ffc0a8aceb9dc4c49d8206a1992b368f29`: REQUEST CHANGES BEFORE MERGE.** An asynchronous `CancelledError` after an upstream POST accepted at T2 left Session without floor/issue, enabling an unsafe T1 write. This is fixed in integration-only code and remains **pending independent signoff**. Full evidence, root cause, safe cleanup and test matrix: [SAIN_Stage1_Cancellation_Safety_Remediation.md](SAIN_Stage1_Cancellation_Safety_Remediation.md).

The independent final acceptance of SHA `def405ffc...` found a NEW MR-NEW-04 P1: `asyncio.CancelledError` after an upstream T2 action committed did not move ClientSession floor, despite Room knowing mutation_possible. Original supplied independent API probe reproduced **T1 second POST 200**. The fix **does not** replace the existing temporal protocol or Stage 1 architecture: Room journal on cancellation sealed uncertain; Session caches same-key ActionFailure and advances floor synchronously before lock release; no automatic POST replay. [Detailed report](SAIN_Stage1_Cancellation_Safety_Remediation.md). Both API routes, composite commands, failed GET, expiry and actual Task.cancel are in separate new regression files. Previous MR-NEW-01/02/03 tests unchanged except the older network-abort mock acceptance now enforces fail-closed behavior and explicit reconnect.

**Green pre-documentation source checkpoint:** `bfff9048c85340f63451bf2c5b373e65eb5ef8e7`, backend [45037464859](https://github.com/nikamurkaa/sain-hack-2026-4Sain/actions/runs/45037464859) 330 tests, frontend [45037464823](https://github.com/nikamurkaa/sain-hack-2026-4Sain/actions/runs/45037464823) 43 Chromium and 43 Firefox, Windows [45037464825](https://github.com/nikamurkaa/sain-hack-2026-4Sain/actions/runs/45037464825) success. The later actual Task.cancel regression and docs require a NEW final exact-HEAD triad before any re-review; see PR description for final SHA and checks. All original six Stage 1 merge parents and base main remain untouched.