# SAIN Stage 1 — Independent Merge Review Remediation

Date: 2026-11-22 · Existing Draft PR [#20](https://github.com/nikamurkaa/sain-hack-2026-4Sain/pull/20) · Integration branch: `integration/stage1-foundation-acceptance`.

## Review basis and integrity

Independent reviewer verdict: **REQUEST CHANGES BEFORE MERGE** on original integration SHA `91c0681cb9bbe25d35b8a1d22499e44b33ccd6ed`. All work stays in this branch; base main remains `2820222613c4ea4544b715435aeba59988470783`. Original #14–19 remain source-of-truth independent Draft PR history. No production merge, deployed app, official token, closed /run, private kit or historical tag manipulation.

**Exact final SHA = live PR #20 head**, which is necessarily generated *by* the commit containing this document. Use PR checks and [Actions](https://github.com/nikamurkaa/sain-hack-2026-4Sain/actions) for its backend/frontend/Windows runs. The code-only checkpoint `5be7f4c05974b31f8bfc8dd0dae6c091162151f5` is not substituted for the final docs-commit SHA. Before that checkpoint, `9513be50fe7d2385cd799565effdea7f7db159b4` had green 303 pytest, 10/60, 28 Chromium + 28 Firefox. After adding exact R8 ±1h tests, [backend run 45028432526](https://github.com/nikamurkaa/sain-hack-2026-4Sain/actions/runs/45028432526) passed **305 pytest**, 1 warning, two successful 10/60; docs commit requires a fresh final check.

## Remediation matrix

| ID | Root cause | Changed files | Red regression → confirmed positive test | CI evidence / status |
|---|---|---|---|---|
| **MR-001 · P1** | Frontend ApiError silently dropped code, operation ID and confirmed device IDs; shared generic retry UX misrepresented partial state | `frontend/src/api.ts`, `actionFeedback.ts`, `ActionNotice.tsx`, `main.tsx`, `design/MobileStay.tsx`, `design/layout.css`, `style.css`, `tsconfig.json`; `scripts/rehearse_client.py`; new browser/backend/node tests | Red [45027331815](https://github.com/nikamurkaa/sain-hack-2026-4Sain/actions/runs/45027331815) missing typed export; new Node typed validation and real FastAPI MockTransport 409 with confirmed light, rejected second sound, exact cached 409 on same key, no POST retry, actual GET, stale GET, conflict, uncertain. E2E Chromium/Firefox screens 375×812 and 1440×900, keyboard focus/Enter, no false done | [Backend green 45027979302](https://github.com/nikamurkaa/sain-hack-2026-4Sain/actions/runs/45027979302); [frontend 45027979275](https://github.com/nikamurkaa/sain-hack-2026-4Sain/actions/runs/45027979275) 10 Node + 28 Chromium + 28 Firefox passed (intermediate SHA). **IMPLEMENTED; awaiting independent re-review and final-head CI.** |
| **MR-002 · P1** | `_local_alarm` throws domain `Refusal` on DST gaps/folds, but manual devices handler did not catch it | `main.py`, `tests/stage1/test_mr002_alarm_contract.py` | Red [45027331816](https://github.com/nikamurkaa/sain-hack-2026-4Sain/actions/runs/45027331816): four actual FastAPI HTTP 500s. Fixed 422 `INVALID_TIME`, stable same-idempotency replay, diff-body 409, no simulator writes or changed alarm; Berlin/NY gap/fold, Moscow, valid neighboring clocks and next-day | [Green 45028432526](https://github.com/nikamurkaa/sain-hack-2026-4Sain/actions/runs/45028432526). **IMPLEMENTED; waiting for independent re-review and final-head CI.** |
| **MR-003 · P2** | Python aware datetime with same ZoneInfo can compare local wall fields instead of chronological UTC instants; nonexistent local wall time was not resolved deterministically | `backend/scheduler.py`, `tests/stage1/test_mr003_bedtime_fold.py` | Red [45027331816](https://github.com/nikamurkaa/sain-hack-2026-4Sain/actions/runs/45027331816): wrong previous-day New York bedtime and invalid gap 02:30. Correct choose earlier fold occurrence, shift gap forward 03:30, compare candidate/wake UTC, apply R8 ±1 real UTC hour, sort every scenario event | [Green 305 pytest 45028432526](https://github.com/nikamurkaa/sain-hack-2026-4Sain/actions/runs/45028432526). **IMPLEMENTED; awaiting independent re-review and final-head CI.** |
| **MR-004 · CI policy** | Default GitHub PR checkout used synthetic merge commit even with identical Git tree | `.github/workflows/test.yml` | Red provenance: prior [45024448298](https://github.com/nikamurkaa/sain-hack-2026-4Sain/actions/runs/45024448298) ran merge ref. Fixed `actions/checkout@v5` with `github.event.pull_request.head.sha || github.sha`, `persist-credentials: false`, assertion `git rev-parse HEAD`, logged expected/actual SHA; retained tests and `contents: read` | [Actual matching checkout log in 45027979302](https://github.com/nikamurkaa/sain-hack-2026-4Sain/actions/runs/45027979302). **IMPLEMENTED; final three-workflow SHA gate pending.** |

## MR-001 end-to-end evidence and semantics

Synthetic phrases are accepted *only* by `scripts.rehearse_client.RehearsalModel`, with action injection *only* in the local MockTransport; they cannot reach the official simulator. Reproducible flow:
1. A synthetic dev session sends `Проверка частичного выполнения` through `POST /api/v1/messages`, with a stable Idempotency-Key.
2. The real local room HTTP transport confirms `light` on the first POST and rejects `sound` on the second POST. `Room.execute` raises `ActionFailure("ACTION_PARTIAL", operation_id, ["light"])`.
3. FastAPI sends HTTP 409 JSON with `code`, `message`, `operation_id`, `confirmed_devices`. A repeat with identical key returns **identical** response, zero new POSTs; reused key with different request body returns `IDEMPOTENCY_CONFLICT` 409.
4. Browser `ApiError` parser accepts only safe known action codes, bounded opaque operation IDs and unique allowlisted device IDs; unexpected JSON falls back to generic ApiError with no invented device confirmations.
5. React shows “Просьба выполнена частично”; “Подтверждённо изменены: Свет”; clearly unconfirmed changes; no general “Готово”, no whole-request retry. A GET-only “Обновить состояние номера” button refreshes actual snapshot, or keeps it explicitly stale when GET fails. An unverified operation blocks new writes until confirmed read.
6. `frontend/tests/stage1-partial.spec.ts` exercises Chromium and Firefox at 375×812 and 1440×900 with screenshots `frontend/evidence/mr001-partial-{chromium,firefox}-{mobile,desktop}.png`, plus keyboard Enter, stale GET, uncertain GET, conflict, session reload.
7. Existing Playwright regression independently covers final read-only, token expiry, idempotent message delivery, manual controls and responsive layouts.

**Screenshots:** inspect `browser-screens` artifact under the **final frontend exact-HEAD run**; earlier real screenshot source [45027979275/artifacts/14756835863](https://github.com/nikamurkaa/sain-hack-2026-4Sain/actions/runs/45027979275/artifacts/14756835863) confirms test creation before the subsequent mobile semantic refinement. Do not replace its files with rendered mocks or Figma frames.

## MR-002 and MR-003 test oracle boundaries

- Four invalid manual HH:MM dates: Berlin 2026-03-29 02:30 gap; Berlin 2026-10-25 02:30 fold; New York 2026-03-08 02:30 gap; New York 2026-11-01 01:30 fold. All must be 422, zero simulation writes, and no 500 or arbitrary fold pick.
- Valid controls include Moscow, before/after DST, tomorrow on a past local HH:MM, same key replay without duplicate action and different key-body conflict.
- Bedtime habitual HH:MM has **no explicit offset**: earliest valid fall fold instant is deterministic (`fold=0`). Spring nonexistent wall time shifts to earliest valid clock after gap, explicitly distinct from manual alarm policy (manual command is **rejected**, since the user is asking for an exact time). The wake and selected bedtime compare in UTC. R8 offsets +1 or −1 **actual elapsed UTC hour**, not misleading wall-clock shift.
- Scenario checks test real event UTC chronology, hotel IANA offsets and boundaries R1/R2/R6/R7; no pre-checkin steps, and R6 under 15 real minutes is physically impossible and cannot be labeled fulfilled.

## CI exact-source and security gate

Backend: `SAIN_SOURCE_SHA=${{ github.event.pull_request.head.sha || github.sha }}`, checkout with same ref, compare `git rev-parse HEAD`, fail on mismatch. Frontend and Windows use their own exact HEAD source assertion. All workflows read-only permissions and no organizer secrets. Backend then executes pinned pip-audit, tracked-file candidate scan, full pytest, offline 10/60 and constrained 1CPU/512MiB 10/60. Frontend executes npm ci/audit, Node unit, TypeScript, Vite, Playwright Chromium+Firefox with actual localhost REHEARSAL, screenshots. Windows packages ZIP and checks checksum, not native Windows run. Official closed API and token use prohibited.

## Architecture / rollback / required reviewer signoff

The support envelope remains single-process, single-worker, per-Room asyncio.Lock, bounded **in-memory** operation journal. No durable recovery of old browser tokens/operation IDs after restart; a new REHEARSAL is a fresh synthetic session. External upstream has no documented authorized reattach or remote exactly-once primitive. SQLite Stage 6, IP/brand rights and native Windows QA remain explicitly out of Stage 1 merge requirements (but block corresponding release claims).

Safe rollback is a normal non-force revert on the integration branch with fresh full CI; existing main/PRs/tags must remain unchanged. Never use a retry to resolve unknown upstream POST results.

**Not approved by an independent reviewer. Not approved for merge.** Once the final docs commit is created, independently check PR #20 final HEAD and all three SUCCESS workflow run **checkout** SHA values, view the real screenshot artifact and separately request the independent re-review. No automatic handoff or merge.
