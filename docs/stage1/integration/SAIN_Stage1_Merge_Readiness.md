# SAIN Stage 1 — Merge Readiness & Independent Review Gate

**Verdict scope:** Integration candidate `integration/stage1-foundation-acceptance`, [Draft PR #20](https://github.com/nikamurkaa/sain-hack-2026-4Sain/pull/20) vs main `2820222613c4ea4544b715435aeba59988470783`.

**Target verdict after confirming every final exact-HEAD check: `STAGE 1 — READY FOR INDEPENDENT REVIEW`.**
This does **not** authorize a merge, public distribution, production use, official API use or certification. If *any* required final check is red/missing, downgrade to `STAGE 1 — NOT READY: FIXABLE BLOCKERS` until new code and complete CI on the new HEAD.

## Hard preconditions
1. Final GitHub PR HEAD SHA verified; Python CI and offline /run normal + 1 CPU/512 MiB pass on that exact SHA.
2. `pip-audit` and bounded tracked-file candidate scan pass on same SHA.
3. `npm ci`, npm high+ audit, TS, Vite build, Chromium/Firefox real-REHEARSAL E2E pass on that same SHA.
4. Windows ZIP build SHA matches exact PR HEAD, archive CRC and per-file SHA256 pass (native Windows launch remains separately NOT VERIFIED).
5. Reviewer sees source ancestry for #14–19, conflicts and new integration regressions, and checks neither main nor historical tag changed.
6. Critical behavior: session creation one POST; no duplicate action on same op ID; truthful partial/uncertain/conflict statuses; R6 legal constraints; DST UTC instant correctness and read-only preview; no invented names; final read-only intact.
7. Independent security/IP review and explicit approval for any external demonstration, never inferred from test success.
8. Owner gives **separate explicit merge permission**; in its absence PR remains Draft.

## Safe merge recommendation (DO NOT EXECUTE NOW)
- Review in this order: #16/#17 joint action protocol, #15 DST UTC correction, #14 R6, #18 neutral name, #19 ADR/risks; then integrated-only commits.
- Inspect all red-to-green source commits, artifact screenshots, backtrace absence, Pydantic error code contracts and complete CI on final HEAD.
- Confirm no branch drift in main, then stage a non-destructive approved merge using normal GitHub protections. Do not force push or delete original PRs/tags.
- If main changes meanwhile, create a **new** tested merge candidate against fresh main, and rerun full suite, rather than assuming older tests remain valid.

## Revert / incident plan
- Before merge: close integrated Draft PR or revert only integration commits by new commits; maintain original branches.
- After an explicitly authorized merge: freeze writes, inspect current actual simulator state, do not reissue uncertain POSTs. Revert via a new reviewed PR and rerun all exact-SHA checks, including data protection and token isolation. Never restore historical organizer infrastructure.
- Test artifacts have GitHub Actions retention expiry; preserve red and green run IDs and source revisions in this folder.

## Formal signoff
Technical evidence can make Stage 1 **reviewable**, not FULLY COMPLETE; S-002/S-024 durable recovery, external API reattachment, brand/IP approval, native Windows acceptance and independent expert review are not closed by CI. Final reviewer and repository owner must separately approve any next action.


---

## 2026-11-22: Independent MR-001–MR-004 remediation (PR #20)

This section supersedes any earlier *merge-readiness claim* in the original Stage 1 document; pre-remediation CI does not establish acceptance of the new HEAD. Full issue-by-issue proof, reproducible tests, red-green SHA links, scope and reviewer questions: [SAIN_Stage1_Merge_Review_Remediation.md](SAIN_Stage1_Merge_Review_Remediation.md).

**Required verdict wording after exact-HEAD checks:** `READY FOR INDEPENDENT RE-REVIEW` or `NOT READY — REMAINING FIXABLE BLOCKERS`. Do not use APPROVED FOR MERGE. The previous document's earlier `READY FOR INDEPENDENT REVIEW` line was superseded by the independent REQUEST CHANGES verdict and this remediation work.

Hard gates: MR-001 structured partial error and safe state-refresh screenshots; MR-002 real HTTP 422 without action; MR-003 fold/gap and ±1h R8 actual UTC; MR-004 backend exact-head provenance; full 10/60+pytest+Python advisory+candidate secrets, npm unit+audit+typecheck+build+Chromium+Firefox local backend E2E, Windows ZIP artifact all on the one **final PR HEAD**. The independent reviewer must explicitly accept these proofs; green CI alone does not approve merge.

No merge, force push, branch deletion, production deployment, closed organizer /run, token use, final read-only bypass, historic tag edit or expert handoff. The existing PR #20 remains Draft until owner decision.

Supported: one process, one worker, in-memory Room journal and API idempotency, loopback REHEARSAL, new session after restart. Unsupported: multi-worker, durable crash replay, remote upstream reattach and exactly-once. Those limitations are carried in the Final ADR and Stage 6 backlog.


---

## TEMPORAL FINAL GATE — MR-NEW-01/02/03 (2026-11-22)

> **Supersedes earlier review-ready claims based on `fb3b082...`.** The independent second review found a new P1 temporal inconsistency; the older 305/28-each green runs are **not** acceptance of the new code. Final disposition requires three new SUCCESS workflows whose jobs checked out the **same last PR HEAD**, independent signoff, and a separate owner merge decision. Full technical explanation: [SAIN_Stage1_Temporal_Recovery_Remediation.md](SAIN_Stage1_Temporal_Recovery_Remediation.md).

**New verdict target:** `READY FOR FINAL INDEPENDENT MERGE REVIEW` only after the four hard conditions below are independently inspected; otherwise `NOT READY — FIXABLE BLOCKERS REMAIN`. Older `READY FOR INDEPENDENT REVIEW` language predates the confirmed second-review MR-NEW-01 failure and is superseded by this section.

1. MR-NEW-01: RED baseline, GREEN T2=20:45 partial snapshot light=0, T1 default light=70 never called verified for T2; both message and manual T1 writes forbidden until correct GET reconciliation, and still forbidden at T1 afterward; same-key replay zero POST.
2. MR-NEW-02: nonempty mobile draft disabled while unresolved, focus/aria hint, no false clickable decorative circle; after GET allowed only conscious new action at next_action_at.
3. MR-NEW-03: real mobile Chromium/Firefox screenshots at low viewport, accessible scroll/keyboard buttons, no overlap with alarm/DND, six devices reachable after dismiss; independent physical QA remains unproven.
4. All backend/online-offline, frontend Chromium+Firefox and Windows ZIP workflows **SUCCESS at identical final commit HEAD**, exact checkout verified. No combining different SHAs; inspect the final run URLs in Draft PR description.

No merge to main, no force push, no official closed /run, no organizer tokens, no tag edit or expert distribution. Upstream atomicity, durable recovery, physical Windows and IP approvals remain external/Stage 6 limitations.


---

## MR-NEW-04 — cancellation safety supersedes earlier merge-readiness claims (2026-11-22)

**Independent reviewer verdict on old SHA `def405ffc0a8aceb9dc4c49d8206a1992b368f29`: REQUEST CHANGES BEFORE MERGE.** An asynchronous `CancelledError` after an upstream POST accepted at T2 left Session without floor/issue, enabling an unsafe T1 write. This is fixed in integration-only code and remains **pending independent signoff**. Full evidence, root cause, safe cleanup and test matrix: [SAIN_Stage1_Cancellation_Safety_Remediation.md](SAIN_Stage1_Cancellation_Safety_Remediation.md).

**Cancellation safety hard gate:** a possible accepted upstream POST on T2 must produce a stable in-memory `mutation_floor >= T2`, journal `uncertain`, server `action_issues` and Idempotency-Key replay before `session.lock` release *even if the task is cancelled*. RED baseline from supplied independent probes; GREEN new real TestClient + direct actual Task.cancel, single-process local only. Browser network loss must read `pending_action` before any default GET or new write. No blind retries, no false done. Manual and message T1 operations must be rejected both before and after reconciliation.

New decision vocabulary after **all three final exact-HEAD CI SUCCESS**: `READY FOR TARGETED INDEPENDENT RE-REVIEW`; otherwise `NOT READY — CANCELLATION SAFETY BLOCKER REMAINS`. Independent approval and separate owner permission still missing; do not merge.

Prior MR-NEW-01/02/03, MR-001–004 retain their tests, semantics and known single-worker limitations. MR-NEW-05 mobile-focus reminder and decorative AI orb cropping are deferred to Stage 4, SQLite/WAL to Stage 6; no native Windows/physical accessibility/official API claims.