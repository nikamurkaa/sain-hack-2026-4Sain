# SAIN Stage 1 — Draft PR Index and Dependency Map

Last review: 2026-11-22. **Base main SHA: 2820222613c4ea4544b715435aeba59988470783.**
All branches below were forked directly from the same baseline main. None was based on another feature branch. All PRs are DRAFT; no merge/force-push/deployment happened. CI entries refer to the **exact** head SHA shown in the same row. If a later commit is pushed, the earlier green run must NOT be treated as verification of the new head.

| PR | IDs | Head branch | Head SHA | Backend CI | Frontend CI | Depends on |
|---|---|---|---|---|---|---|
| [#14](https://github.com/nikamurkaa/sain-hack-2026-4Sain/pull/14) | S-003 | fix/scheduler-short-stay-r6 | 13491b93a014e3550a95f2f6874079c649080340 | [success, 250 pytest + offline](https://github.com/nikamurkaa/sain-hack-2026-4Sain/actions/runs/45022185234) | [success, Chromium/Firefox](https://github.com/nikamurkaa/sain-hack-2026-4Sain/actions/runs/45022185328) | None |
| [#15](https://github.com/nikamurkaa/sain-hack-2026-4Sain/pull/15) | S-004 | fix/virtual-timezone-dst | 6f2f2c6222df9be5d487cc2959e5ce30ce4e125f | [success, 227 pytest + offline](https://github.com/nikamurkaa/sain-hack-2026-4Sain/actions/runs/45021820204) | [success, Chromium/Firefox](https://github.com/nikamurkaa/sain-hack-2026-4Sain/actions/runs/45021820137); [Windows ZIP success](https://github.com/nikamurkaa/sain-hack-2026-4Sain/actions/runs/45021820167) | None |
| [#16](https://github.com/nikamurkaa/sain-hack-2026-4Sain/pull/16) | S-009 | fix/session-idempotency-boundaries | fb916c1d24e7097026134a74ea62392247120f15 | [success, 216 pytest + offline](https://github.com/nikamurkaa/sain-hack-2026-4Sain/actions/runs/45022191988) | [success, Chromium/Firefox](https://github.com/nikamurkaa/sain-hack-2026-4Sain/actions/runs/45022191991) | None |
| [#17](https://github.com/nikamurkaa/sain-hack-2026-4Sain/pull/17) | S-008 | fix/confirmed-partial-actions | 44ae58874ddfa42b26f0ca25c9c5681d882fde9b | [success incl. extended fault injection](https://github.com/nikamurkaa/sain-hack-2026-4Sain/actions/runs/45022544806) | [success, Chromium/Firefox](https://github.com/nikamurkaa/sain-hack-2026-4Sain/actions/runs/45022544860) | None |
| [#18](https://github.com/nikamurkaa/sain-hack-2026-4Sain/pull/18) | S-010 | fix/guest-identity-contract | ad41044caa79242fd6c8be61f8425385c48ffc68 | [success, 215 pytest + offline](https://github.com/nikamurkaa/sain-hack-2026-4Sain/actions/runs/45021875784) | [success, Chromium/Firefox](https://github.com/nikamurkaa/sain-hack-2026-4Sain/actions/runs/45021875785); [Windows ZIP success](https://github.com/nikamurkaa/sain-hack-2026-4Sain/actions/runs/45021875801) | None |
| [#19](https://github.com/nikamurkaa/sain-hack-2026-4Sain/pull/19) | S-002/S-024/S-014/S-023 | docs/stage1-foundation-evidence | See latest PR HEAD (self-index cannot freeze its own SHA) | Documentation-only PR | N/A | References evidence from #14–#18 |

## Red original tests

| PR | Test-first SHA | Red run | Technical interpretation |
|---|---|---|---|
| #14 | 306214d5edb9c436d3a1e53f28852ae1b85d7cd7 | [45021236288](https://github.com/nikamurkaa/sain-hack-2026-4Sain/actions/runs/45021236288) | Short-stay R6 dawn missing legal fallback |
| #15 | db2ca3dc948840eb9ab344e1d8e8b2aa67421705 | [45021239235](https://github.com/nikamurkaa/sain-hack-2026-4Sain/actions/runs/45021239235) | Fixed UTC-offset across DST |
| #16 | 3d0c7ac97e604c1f922f9a700d2a0302c1ce34ef | [45021242085](https://github.com/nikamurkaa/sain-hack-2026-4Sain/actions/runs/45021242085) | Lost creating POST reply causes unsafe replay |
| #17 | 95e60808fe2a9bc9d66ad81fd65388492a91e09a | [45021435357](https://github.com/nikamurkaa/sain-hack-2026-4Sain/actions/runs/45021435357) | No confirmed-step operation journal |
| #18 | a6809015dcc198b1b87a19b91af6d3a62ee71713 | [45021860073](https://github.com/nikamurkaa/sain-hack-2026-4Sain/actions/runs/45021860073) | Figma guest name not sourced from official API |

## Integration dependencies and merge safety

- **Review order suggestion:** #14 and #15 independently, #16 then #17 together in review (both touch backend/room.py and have overlapping retry/reconciliation surfaces), #18, #19. This is an **integration review dependency**, not a feature branch ancestry dependency.
- #14, #16 and #17 each contain the identical .github/workflows/frontend.yml pull_request path expansion to run browser CI for backend diffs. When combining, preserve exactly one copy of that CI rule.
- #16 and #17 both edit backend/room.py and may require explicit conflict resolution; review semantic outcome rather than choosing either diff blindly.
- #15 and #17 both edit main.py; combine IANA validation with partial-error metadata and preserve both.
- No integrated candidate SHA has been created. **Do not assert that the individual CI results cover a hypothetical merged codebase.**
- No PR may be marked ready for external acceptance merely from success of its local scripted tests. Official API, licenses and restart-boundary issues require separate decisions.
- Do not merge to main, publish to production or open official /run until independent review and explicit owner authorization.

## Test evidence locations

- [S-003 Python and browser](https://github.com/nikamurkaa/sain-hack-2026-4Sain/actions/runs/45022185328)
- [S-004 screenshot artifact in successful browser run](https://github.com/nikamurkaa/sain-hack-2026-4Sain/actions/runs/45021820137)
- [S-008 complete saga / fault tests](https://github.com/nikamurkaa/sain-hack-2026-4Sain/actions/runs/45022544806)
- [S-009 non-retry and browser](https://github.com/nikamurkaa/sain-hack-2026-4Sain/actions/runs/45022191991)
- [S-010 actual offline API guest-name test](https://github.com/nikamurkaa/sain-hack-2026-4Sain/actions/runs/45021875785)

GitHub Actions screenshot artifacts have limited retention. Test logs and source commit history remain linkable after artifacts expire, subject to GitHub retention.
