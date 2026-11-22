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
