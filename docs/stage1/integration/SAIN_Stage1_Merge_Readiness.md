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
