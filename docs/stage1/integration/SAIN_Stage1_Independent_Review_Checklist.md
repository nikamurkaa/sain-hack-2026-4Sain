# SAIN Stage 1 — Independent Review Checklist

Check scope: integrated [Draft PR #20](https://github.com/nikamurkaa/sain-hack-2026-4Sain/pull/20), baseline main `2820222613c4ea4544b715435aeba59988470783`. This is a checklist for a reviewer, **not a self-approval**.

## Source integrity and conflicts
- [x] Read all six original PR patches #14–19 and their exact branch HEADs.
- [x] Main baseline confirmed unchanged before creation; all six real Git merge commits preserve second-parent history.
- [x] Resolved backend/room.py (#16 + #17), main.py (#15 + #17) semantically, no ours/theirs blind choice.
- [x] Deduplicated same workflow change in #14/#16/#17, preserving backend-triggered E2E.
- [ ] Reviewer independently verifies merge ancestry, full changed-file diff and no new unknown modifications.
- [ ] Reviewer approves combined integration; Draft PR must remain unmerged until owner approval.

## S-003 R6
- [x] 0–31 real minutes short-stay oracle; 25-minute curtain substitute and normal 3-step dawn.
- [x] Night darkness, DND, catalog bounds, midnight and IANA-zone boundary regression.
- [ ] Review explicit policy for arrival under 15 minutes; no false R6-compliant status.

## S-004 time
- [x] Backend validates date-specific hotel time/offset, rejects nonexistent clocks and distinguishes fall-back folds.
- [x] Independent device-schedule UTC oracle added for Berlin/NY spring and fall and Moscow.
- [x] Preview vs actual state checks and frontend Intl time formatting; GET future state does not mutate confirmed snapshot.
- [ ] Review extremely long future stays and future tzdata rules, outside current fixture.

## S-008 and S-009 correctness
- [x] No automatic repeated POST /room/session after a lost response/503.
- [x] Serial per-room action processing and confirmed full-state checks after each action.
- [x] Before-first, after-first, after-second, lost action POST, GET timeout, concurrent commands, same-key double submit and different-payload idempotency conflict.
- [x] Partial replay retains confirmed devices and truthful status, conflict is distinct.
- [x] Journal full rejects new operation without evicting replay protection.
- [x] API cached partial error retains confirmation metadata.
- [ ] Crash/restart still invalidates journal and guest sessions (intentionally not durable).
- [ ] Review external upstream non-atomic and hidden side-effect limitations; do not claim exactly-once.

## S-010 and UI
- [x] No `display_name` in strict source dataset; neutral UI never infers identity from user ID.
- [x] Browser E2E connects to real localhost REHEARSAL backend; final/dev and token isolation.
- [x] Final read-only HTTP 409 preserved; no closed /run or unofficial endpoints.
- [ ] Manual accessibility/visual review of partial error presentation and screenshots on physical devices.

## Security, performance, documentation
- [x] Bounded tracked-file secrets gate and public advisory checks included in Stage 1 CI.
- [x] Release-grade claims explicitly separated from scripted LLM and fake STT.
- [x] Linux-built Windows ZIP hash/manifest verification; no native Windows launch claim.
- [x] External brand/asset/official API/license approvals remain pending and separated.
- [ ] Full historical Git blob+artifact secret scan and legal ownership check require independent work.
- [ ] Reviewer validates public CVE database results and npm/pip audit logs at final SHA.

## Final SHA acceptance
- [ ] Record EXACT PR HEAD SHA before reviewing checks.
- [ ] Python pytest + 10/60 two runs + R1–R8 green at that SHA.
- [ ] Python advisory and secrets candidate gate green at that SHA.
- [ ] npm ci + npm audit + TS + production build green at that SHA.
- [ ] Chromium and Firefox E2E green at that SHA; open screenshot artifact and inspect changed states.
- [ ] Windows ZIP workflow green at that SHA; acknowledge Linux packaging vs Windows native execution.
- [ ] All pre-merge blocking review comments addressed and external risks explicitly accepted/assigned.
- [ ] Owner gives separate explicit permission to merge; **do not merge from this checklist**.

Failure to meet any executable CI item is `NOT READY: FIXABLE BLOCKERS`. A green CI is necessary but not sufficient for approval to publish, operate with official tokens, or claim a durable multi-tenant service.


---

## 2026-11-22: Independent MR-001–MR-004 remediation (PR #20)

This section supersedes any earlier *merge-readiness claim* in the original Stage 1 document; pre-remediation CI does not establish acceptance of the new HEAD. Full issue-by-issue proof, reproducible tests, red-green SHA links, scope and reviewer questions: [SAIN_Stage1_Merge_Review_Remediation.md](SAIN_Stage1_Merge_Review_Remediation.md).

### MR-specific independent reviewer actions
- [x] MR-001: reproducing Node failure committed before fix; action code, operation ID, device list are validated and retained; no blind whole-request repeat after partial/uncertain.
- [x] MR-001: local FastAPI + MockTransport fault injection tests and Chromium/Firefox Playwright cover real HTTP 409 → typed client → UI → safe GET; screenshots generated automatically at 375×812 and 1440×900.
- [x] MR-001: alert semantics, keyboard focus/Enter on GET-only button, no generic final-lock interpretation of unrelated 409.
- [x] MR-002: 4 DST invalid clock requests return 422/INVALID_TIME on a real TestClient, no POST; cached refusal fingerprint rejects different-body reuse.
- [x] MR-003: UTC chronological comparisons, explicit first-fold and forward-gap policy, real-hour R8 +1/−1 tests.
- [x] MR-004: backend exact-head checkout, SHA assert, least privilege; frontend and Windows exact-head source guards retained.
- [ ] Independently inspect `frontend/evidence/mr001-partial-*.png` from the **latest** `browser-screens` artifact and verify visual accessibility/readability.
- [ ] Independently repeat failure scenarios and challenge fault-injection test oracle (local-only fixture, no official API).
- [ ] Confirm **three final CI success runs use precisely the same final PR HEAD SHA** and no temporary merge ref executed.
- [ ] Confirm original #14–19 and main unchanged and PR #20 still Draft.
- [ ] Independent re-review, owner's separate merge permission and any future external legal/brand approval are **not granted here**.

Stage 1 restart state remains in-memory; one worker/process only. A new synthetic REHEARSAL session after restart is *not* recovered old state.
