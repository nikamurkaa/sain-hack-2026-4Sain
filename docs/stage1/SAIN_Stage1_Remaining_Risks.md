# SAIN Stage 1 — Remaining Risks, Blockers & Next Stages

Date: 2026-11-22. Base main SHA: 2820222613c4ea4544b715435aeba59988470783.
**Verdict: PARTIAL.** No code from Stage 1 was merged into main. This file distinguishes verified local fixes from missing integration evidence and external approvals.

| ID | Severity | Residual risk / evidence | Why not marked DONE | Next stage / gate |
|---|---|---|---|---|
| S-002 | P1 | In-memory app.state.sessions/run_cache/final_session and per-room operations | No persisted authorized reattachment or safe reconciliation after process restart | Stage 6 (Persistence & Operations) after ADR-002 contract/retention approval |
| S-024 | P2 | Room.operations journal records confirmed steps but only in-process; history is ephemeral | No durable Event, commands, correlation across crashes | Stage 6 with SQLite WAL and migrations; reconcilable local simulator |
| S-003 | P1 | R6 requires 3 rises in 15–30m OR curtain opening; both impossible when check-in less than 15m before wake | Cannot schedule before check-in to satisfy a rule that started in the past. Current patch truthfully makes no false promise; impossibility not separately exposed in API | Stage 2 policy for truly impossible windows and auditable constraint resolution |
| S-004 | P1 | Fixed-offset preview corrected using IANA zone; backend validates supplied offset | Full matrix of arbitrary future geographic time-rule changes not covered; legacy fallback still supports unannotated responses | Stage 6 time data/version policy; maintain regression for future tzdata |
| S-008 | P1 | No simulator atomic multi-command transaction | Fail-closed sequential action saga reports confirmed devices but cannot roll back an already applied action; operation journal not durable | Stage 6 durable reconciliation; external API capability if available |
| S-009 | P1/HYPOTHESIS | Official upstream may create an object before returning transport timeout | Local unsafe retry removed; official API behavior and idempotency support remain unverified because official endpoints must not be called | Stage 2/6 documented API contract and explicitly authorized fault testing |
| S-010 | P2 | No trustworthy user display_name in official strict Case2 schema | UI now uses neutral title. Personal greeting is intentionally out of scope; cannot invent name | Stage 2 only with opt-in identity field and privacy-reviewed contract |
| S-014 | P1 | Filename-level main history scan + manifest/CI review; no full content audit or key verification | 80 main-visible commits checked by changed **paths** and present tree, but no full review of all Git object bytes, PR branch history, removed blobs, artifact contents, key lifetimes or CVE feeds. Never extract private ZIP material into public reports | Stage 6 complete secret scanning, dependency audits and incident/key rotation process |
| S-023 | P1/EXTERNAL | SAIN brand/API/assets and handoff use require permission | Source licenses and hackathon participation are not a blanket post-event redistribution or API license | Written authorization + asset inventory before Stage 7 expert handoff |
| S-001 | External | Final read-only HTTP 409 boundary | Intentionally unchanged and never bypassed | Independently authorized demo adapter / new agreement, Stage 2 |
| S-006/S-013 | P1 | 19 scripted intentions and fake STT not genuine model accuracy | Official tokens were not used and offline pass ≠ live AI quality | Stage 2/3 private authorized benchmark, blind utterances, real STT |
| S-011 | UI | Responsive and premium design require physical device, a11y and visual review | Chromium/Firefox is useful but not native mobile evidence or pixel-perfect Figma diff | Stage 4 |
| Security | P1 | GitHub Actions actions use moving major tags and npm dependencies use semver ranges | Proven reproducible npm ci package lock, but not full dependency advisory, SLSA or pin-by-SHA audit | Stage 6 |
| Cross-PR integration | P1 | Each of five PRs was separately built from same main | No single SHA yet includes and tests all five PRs together, so interactions remain unproven | **Mandatory integration candidate branch and re-run all CI before any merge** |
| Windows native | P2 | Windows ZIP built in Linux GitHub Actions | Actual Windows START.cmd/STOP.cmd validation not executed by this stage | Stage 7 native acceptance |
| Expert review | EXTERNAL | No experts contacted and no materials sent | User explicitly prohibited external handoff and requires independent review before merge | Stage 7 only after permission and owner's approval |

## Required safety controls for remaining work

- Keep all feature PRs as Draft, do not merge, force push, deploy, run official /run, use organizers' credentials or alter historical tag.
- Always separate actual/confirmed snapshots from planned scenario timestamps; a future preview is GET-only.
- Never assert a session was created from an uncertain POST response; do not retry blindly.
- Never describe partial device completion as successful completion.
- User names appear only when independently provided and authorized by source data; no inferred identities.
- Do not persist raw microphone audio, bearer credentials, private starter ZIP, tokens or unrestricted conversation history.
- Keep a pending external approvals register at repository root: EXTERNAL_APPROVALS.md.

## Proposed next execution order

1. Finish all Draft PR branch CI at their exact SHAs (Python, offline 10/60, TypeScript, Chromium/Firefox, Windows package where triggered).
2. Independent engineering review of each PR including original failing commit, fix, and rollback.
3. Owner-approved temporary **integration branch only** from main (do not merge to main) incorporating reviewed changes, resolving any shared CI-workflow overlap and running full checks on the resulting SHA.
4. Preserve artifacts, validate independent 19-intent and R1–R8 oracle on the integrated branch, verify final/dev permissions.
5. Plan Stage 2 impossible-window policy and official case completion; Stage 6 durable state only if a supported local-only or explicitly licensed upstream architecture is available.
6. Gain written IP/brand/API permission and complete independent Stage 7 acceptance before third-party demo.

## Definition of Done status

**PARTIAL**, not COMPLETE. Individual defects have isolated fixes and evidence, but durability and comprehensive combined/external acceptance are not solved, and no merge approval was given.
