# SAIN Stage 1 — Regression Matrix

Evidence captured: 2026-11-22. Baseline main: 2820222613c4ea4544b715435aeba59988470783.
**Important:** CI executes each Draft PR independently against main; no combined integration merge SHA has been built or tested. A green CI badge does not prove live LLM/STT, third-party licensing, native Windows or production readiness.

## Exact per-branch regression evidence

| PR / issue | exact HEAD SHA | RED regression SHA / red run | GREEN backend | GREEN frontend / Windows |
|---|---|---|---|---|
| #14 S-003 | 13491b93a014e3550a95f2f6874079c649080340 | 306214d5edb9c436d3a1e53f28852ae1b85d7cd7 / [red 45021236288](https://github.com/nikamurkaa/sain-hack-2026-4Sain/actions/runs/45021236288) | [250 passed + offline](https://github.com/nikamurkaa/sain-hack-2026-4Sain/actions/runs/45022185234) | [Browser 45022185328](https://github.com/nikamurkaa/sain-hack-2026-4Sain/actions/runs/45022185328); verify final outcome in Actions |
| #15 S-004 | 6f2f2c6222df9be5d487cc2959e5ce30ce4e125f | db2ca3dc948840eb9ab344e1d8e8b2aa67421705 / [red 45021239235](https://github.com/nikamurkaa/sain-hack-2026-4Sain/actions/runs/45021239235) | [227 passed + offline](https://github.com/nikamurkaa/sain-hack-2026-4Sain/actions/runs/45021820204) | [Browser success](https://github.com/nikamurkaa/sain-hack-2026-4Sain/actions/runs/45021820137), [Windows build success](https://github.com/nikamurkaa/sain-hack-2026-4Sain/actions/runs/45021820167) |
| #17 S-008 | ed86a7ca21f2542701f89547305b9945c4c277fe | 95e60808fe2a9bc9d66ad81fd65388492a91e09a / [red 45021435357](https://github.com/nikamurkaa/sain-hack-2026-4Sain/actions/runs/45021435357) | [219 passed + offline](https://github.com/nikamurkaa/sain-hack-2026-4Sain/actions/runs/45022188976) | [Browser success](https://github.com/nikamurkaa/sain-hack-2026-4Sain/actions/runs/45022188964) |
| #16 S-009 | fb916c1d24e7097026134a74ea62392247120f15 | 3d0c7ac97e604c1f922f9a700d2a0302c1ce34ef / [red 45021242085](https://github.com/nikamurkaa/sain-hack-2026-4Sain/actions/runs/45021242085) | [216 passed + offline](https://github.com/nikamurkaa/sain-hack-2026-4Sain/actions/runs/45022191988) | [Browser 45022191991](https://github.com/nikamurkaa/sain-hack-2026-4Sain/actions/runs/45022191991); verify final outcome in Actions |
| #18 S-010 | ad41044caa79242fd6c8be61f8425385c48ffc68 | a6809015dcc198b1b87a19b91af6d3a62ee71713 / [red Playwright](https://github.com/nikamurkaa/sain-hack-2026-4Sain/actions/runs/45021860073) | [215 passed + offline](https://github.com/nikamurkaa/sain-hack-2026-4Sain/actions/runs/45021875784) | [Browser success](https://github.com/nikamurkaa/sain-hack-2026-4Sain/actions/runs/45021875785), [Windows build success](https://github.com/nikamurkaa/sain-hack-2026-4Sain/actions/runs/45021875801) |

The backend workflow includes: Python pytest, offline HTTP /run with a synthetic 10-stay/60-request fixture, and a second offline /run execution under one CPU and 512 MiB. The frontend workflow includes: npm ci, Node unit tests, TypeScript typecheck, Vite production build, Chromium and Firefox Playwright E2E, and screenshot artifacts. Windows package workflow creates a ZIP under Linux CI; **it does not establish native Windows execution**.

## Functional matrix (verified scope)

| Area | Test / oracle | Result in isolated PR tests | Limit |
|---|---|---|---|
| 19 intent families | tests/offline_cases.py CASES + tests/test_final_score_gate.py + plan_commands | PASS scripted / deterministic | Live NLU accuracy NOT TESTED |
| 10 synthetic stays | scripts/check_offline.py, independent scripts/sleep_audit.py | PASS standard fixture | Not all possible stays |
| 60 synthetic requests | check_offline, simulator state and schema | PASS standard fixture | Deliberately injected 503 can legitimately omit unconfirmed session |
| R1–R8 standard fixture | independent sleep_audit and manual oracle tests | PASS | R1–R8 impossible windows still require defined product policy |
| R6 short stay 0–31 min | tests/stage1/test_r6_short_stay.py, three-light or curtain oracle | PASS #14 | For check-in <15 min before wake, legal R6 window cannot be reached |
| Midnight, Moscow/Berlin/NY | parameterized scheduler tests + hotel_moment | PASS #14/#15 independently | Combined branches not yet tested together |
| DST spring-forward | Berlin nonexistent clock and New York spring case | PASS #15 | Does not validate arbitrary geopolitical timezone rule changes |
| DST fall-back / ambiguous hour | explicit +/- offsets for Berlin and NY | PASS #15 | Natural language alarm clarification remains policy-bound |
| Virtual preview vs actual state | tests/test_preview_snapshot_isolation.py; frontend E2E real localhost | PASS #15 | Preview timestamp is not a command |
| Six devices / range checks | tests/test_manual_devices.py, catalog, Py tests | PASS | Synthetic simulator, no physical hardware |
| Medical/out-of-scope refusals | tests/offline_cases.py, Intent/Refusal tests | PASS scripted | Live model refusals NOT TESTED |
| No extraneous changes | independent full-state comparison for requests | PASS standard fixture | External concurrent actor tested in fault-injection only |
| Failed first/second action, lost POST response | tests/stage1/test_partial_operations.py | PASS #17 | Journal in-memory, non-atomic upstream |
| GET timeout / external state drift | same independent fault-injection suite | PASS #17 | Unknown outcome stays UNKNOWN |
| Double-submit / idempotency | same suite, tests/test_integration.py, test_manual_devices.py | PASS within process | No cross-restart exactly-once guarantee |
| Upstream session creation retry | tests/stage1/test_session_post_retries.py and corrected 503 expectation | PASS #16 | Actual upstream duplication HYPOTHESIS not proven |
| Guest name absent | official Case2Dataset strict schema + tests/stage1-identity.spec.ts real offline API | PASS #18 | No trusted name exists in source; neutral UI only |
| Restart behavior | tests/test_rehearsal_recovery.py and architecture ADR | PASS fail-closed restart behavior | Durable recovery NOT IMPLEMENTED |
| Concurrent processing | tests/test_integration.py bounded concurrency and locks | PASS synthetic | Multi-worker deployment not supported |
| Session isolation / final read-only | tests/test_conversation.py, test_manual_devices.py and browser E2E | PASS synthetic | Official final API NOT contacted |
| Pydantic/API contract | tests/test_integration.py OpenAPI model verification + pytest | PASS | Versioned public clients not exercised |
| Voice/STT | scripted fake STT and browser microphone tests | PASS fake | Real transcription unavailable and not claimed |
| Asset/legal/supply chain review | filenames, manifests, CI configuration, license text presence | PARTIAL | No full blob secret scan or external license confirmation |
| Combined PR integration | None; PRs branch from same main | NOT TESTED | Must run after reviewed integration branch before any merge |
| Actual native Windows | Windows ZIP CI only | NOT TESTED | Requires approved device and manual QA |

## Red-to-green proof

- S-003: new short-stay oracle fails original scheduler with two rises, then passes after legal curtain fallback.
- S-004: new TypeScript DST tests fail with stale offset, then pass with IANA conversion. Later tests corrected their selected time range: the old test erroneously expected an hourly synthesized 06:00 to outrank an actual end-of-stay event at 07:00/08:00; tests now put the end-of-stay in afternoon, preserving the intended DST oracle. Backend IANA tests added independently.
- S-008: new tests first fail for missing operation ID/status and partial confirmation semantics, then pass with fail-closed journal; no claim of atomic upstream transaction.
- S-009: synthetic lost POST reply demonstrated an unsafe repeat in old code. Earlier golden test demanded 3 retries of a state-creating POST after 503; that assertion was corrected because the API has no documented idempotency guarantee. It now expects one attempt and an omitted unconfirmed request, never a fabricated ID.
- S-010: original virtual mobile heading retained an invented Figma name. New real-offline-API browser test failed, then passed with neutral heading.

## Screenshot and CI artifacts

- S-004: [browser-screens, artifact 14753873530](https://github.com/nikamurkaa/sain-hack-2026-4Sain/actions/runs/45021820137), generated by Chromium E2E and uploaded by the workflow.
- S-008: [browser-screens, artifact 14754168202](https://github.com/nikamurkaa/sain-hack-2026-4Sain/actions/runs/45022188964).
- S-010: [browser-screens, artifact 14753857453](https://github.com/nikamurkaa/sain-hack-2026-4Sain/actions/runs/45021875785).
- Artifacts are temporary GitHub Actions attachments with their configured retention period. The presence of a screenshot archive is not a pixel-perfect visual acceptance verdict.

## Remaining acceptance gap

**Stage 1 is PARTIAL until:** the last cross-stack runs are successful, independent integration of all five PR changes on one candidate is tested without modifying main, the external licensing/security questions are closed separately, and a storage decision can be implemented without falsely promising recovery. See Remaining Risks and Architecture Decisions.
