# SAIN Stage 1 — Cancellation Safety Remediation (MR-NEW-04)

**Дата:** 22 ноября 2026 · **Команда:** 4Sain · **Объект:** [открытый Draft PR №20](https://github.com/nikamurkaa/sain-hack-2026-4Sain/pull/20) (`integration/stage1-foundation-acceptance` → `main`). **Не является независимым одобрением или разрешением на merge.**

## 1. Принятая независимая оценка и RED

**Базовый подтверждённый исходник:** `def405ffc0a8aceb9dc4c49d8206a1992b368f29`, `main`: `2820222613c4ea4544b715435aeba59988470783`. По приложенным `SAIN_Stage1_Final_Independent_Acceptance(2).md` и `SAIN_Stage1_Independent_Evidence(2).zip`, включая `evidence/independent_api_probes.py` / `api-probes.log`, независимый reviewer вынес **REQUEST CHANGES BEFORE MERGE**: на реальном локальном FastAPI TestClient + MockSimulator, при принятых 20:45 light=0 и последующем `asyncio.CancelledError`, у Room был `in_progress` с `mutation_possible=True`, но у ClientSession остались `mutation_floor=None`, `action_issues={}`. Повтор новой командой в 20:00 возвращал HTTP200 и создавал **второй upstream POST**.

В локально извлечённом **неизменённом Windows release exact-SHA `def405ffc...`** воспроизведён оригинальный `independent_api_probes.py`: `first_http=500`, `old_time_replay_http=200`, `upstream_post_delta=2`. Дополнительный RED regression создан отдельным коммитом [a2cb2d5](https://github.com/nikamurkaa/sain-hack-2026-4Sain/commit/a2cb2d5d3103fc7f993d4a6ed61a2c8ed566ce05) **до исправления производственного кода**: `tests/stage1/test_mr_new04_cancellation.py`. Тот же файл на прежнем исходнике показал **3 failures**. В промежуточной первой попытке исправить только Room [backend CI 45036473916](https://github.com/nikamurkaa/sain-hack-2026-4Sain/actions/runs/45036473916) вновь получил **3 failed, 311 passed**: Room журнал уже uncertain, но Session floor/issue по-прежнему отсутствовали. Это независимое RED-доказательство недостаточности одностороннего исправления.

## 2. Первопричина

`Room._execute_locked` отмечал `mutation_possible=True` перед `await client.request("POST", "/action")`. Но `asyncio.CancelledError` не наследуется от `ServiceError` и обходил обработчики в `backend/room.py` и в обеих API-ветках `main.py`. Поэтому синхронизация по `register_action_failure` вообще не происходила. ClientSession блокировка сериализовала запросы, но сама по себе **не** гарантировала commit bookkeeping при отмене.

## 3. Новая fail-closed политика

**Room level:** `Room.execute` под `_execute_lock` запоминает идентификаторы уже существовавших операций, затем явно перехватывает `asyncio.CancelledError`; только записи, созданные текущим вызовом и оставшиеся `in_progress`, **синхронно** завершаются как `uncertain` с сохранением `operation_id`, `attempted_at`, `mutation_possible`, всех подтверждённых устройств и исходного state. Устанавливается кешируемая `ACTION_UNCERTAIN`-ошибка; Task cancellation **повторно выбрасывается**, а не маскируется.

**ClientSession level:** каждый обработчик `POST /api/v1/messages` и `POST /api/v1/devices` сохраняет snapshot Room operation IDs перед первым потенциальным await действующей команды. В отдельном `except asyncio.CancelledError`, **пока ещё удерживается `session.lock`**, `record_cancelled_action` синхронно сопоставляет новые Room записи с оригинальным HTTP fingerprint/Idempotency-Key, сохраняет `ActionFailure(ACTION_UNCERTAIN)` в `session.messages`, регистрирует `action_issues[operation_id]` и продвигает `mutation_floor` до `attempted_at` если `mutation_possible`. Список ранее подтверждённых устройств остаётся точным; отсутствующее подтверждение **не выдумывается**. При отмене до первой передачи POST создаётся консервативный unknown record без фальшивых эффектов: pending блокирует записи, пока GET не сверит состояние. Отмена затем честно пробрасывается на ASGI boundary.

**Ключевое свойство:** в **критическом cleanup нет новых `await`**. Поэтому никакая повторная отмена во время освобождения lock не может прервать в-памяти фиксацию. `asyncio.shield` **не используется**: нет скрытых фоновых незавершённых POST после отказа клиента, а lock освобождается штатным `async with` после синхронной регистрации. Универсальный `except BaseException` не применяется. Эта гарантия относится к одному процессу/worker, не к crash/restart.

**Idempotency:** исходный key + fingerprint сохранены. Повтор key с тем же payload даёт тот же `ACTION_UNCERTAIN 409` и стабильные `operation_id/attempted_at/confirmed_devices`, **не отправляет** новый POST. Иной payload на том же key — `IDEMPOTENCY_CONFLICT`. Новый key до recovery — `RECOVERY_REQUIRED 409`; после recovery запись раньше `mutation_floor` — `TIME_BACKWARDS 409`. Защита общая для обоих API.

**Reconciliation:** уже существующий авторизованный `GET /api/v1/reconciliation?operation_id=...` читает **T2**, проверяет известные подтверждённые устройства относительно журнала Room, возвращает сохраняемый `status=uncertain`, verified snapshot и `next_action_at>=T2`. Не повторяет POST. При GET ошибке pending и запрет новых writes сохраняются. `GET /state?at=...` — read-only virtual preview и сам по себе не снимает pending. Чужая сессия не получает op metadata (404). `done` и успешная история **не** создаются при отмене.

## 4. Что изменилось: Room и ClientSession

| Сущность | Было после CancelledError в T2 | Стало после CancelledError в T2 |
|---|---|---|
| `Room.operations[opid].status` | `in_progress` навсегда | `uncertain` + сериализованный error для последующего replay |
| `Room.operations[opid].mutation_possible` | `True` | `True`, без утери |
| `confirmed_devices` | Положительные записи иногда сохранялись только в Room | Сохраняются в обоих журналах, ни одна неизвестная не помечается подтверждённой |
| `ClientSession.action_issues[opid]` | Отсутствует | `code=ACTION_UNCERTAIN`, `status=uncertain`, `attempted_at=T2`, `verified=False` |
| `ClientSession.mutation_floor` | `None` | Минимум T2 в реальных UTC instants, если POST мог произойти |
| `ClientSession.messages[Idempotency-Key]` | Общий placeholder без op ID | Кеширован `ActionFailure` того же исходного fingerprint и op ID |
| Следующая запись на T1 | Ошибочно HTTP 200 | До GET HTTP 409 `RECOVERY_REQUIRED`; после GET HTTP 409 `TIME_BACKWARDS` |
| Новые upstream POST при чтении/повторе | Было 2 при новой T1-команде | Остаётся 1 до новой разрешённой явной T2-команды; после неё — 2 |

## 5. Дополнительный frontend recovery

Браузерная обработка `POST` без ответа (HTTP500, network abort, timeout) теперь выставляет fail-closed локальную блокировку `unansweredPost`. Сначала запрашивается **авторизованный `/session`**, а не GET старого времени T1. Если сервер возвращает `reconciliation_required` и типизированный `pending_action`, frontend валидирует его через существующий parser, показывает `ACTION_UNCERTAIN` со стабильным `operation_id/attempted_at` и читает тот же авторизованный `GET /reconciliation`. Если GET не удался, UI остаётся stale/disabled, без automatic POST. Переподключение с ещё действующим тем же гостевым токеном снова видит pending. В отсутствие серверного доказательства состояния пользователь не может скрытым образом разблокировать кнопку просто закрыв сетевое уведомление; только проверка сервера/новый сознательный сеанс.

**Сквозная REHEARSAL-инъекция:** сугубо в `scripts/rehearse_client.py` phrase `Проверка отмены после принятия` вызывает синтетический `asyncio.CancelledError` **после настоящего локального MockTransport POST**, плюс три неудачных safe GET. Это не production endpoint, не обращение к организаторам. Chromium/Firefox проверяют запись в T2 при начальном T1, отсутствие авто-повтора, disabled с непустым draft, reconnect и последующее безопасное продолжение в T2.

## 6. Список файлов, RED→GREEN и фактические тесты

| Слой | Файлы |
|---|---|
| Backend | `backend/room.py`, `main.py` |
| Frontend | `frontend/src/main.tsx` |
| Изолированный REHEARSAL fixture | `scripts/rehearse_client.py` |
| Новые тесты | `tests/stage1/test_mr_new04_cancellation.py`, `tests/stage1/test_mr_new04_matrix.py`, `frontend/tests/stage1-cancellation.spec.ts` |
| Уточнённый старый тестовый oracle | `frontend/tests/screens.spec.ts`: после unknown transport failure требуется подтверждённое переподключение, а не произвольная повторная запись |
| Документы | этот файл, `SAIN_Stage1_Final_Regression_Matrix.md`, `SAIN_Stage1_Merge_Readiness.md`, `SAIN_Stage1_Open_Risks.md`, `SAIN_Stage1_Integration_Report.md`, `SAIN_Stage1_Independent_Review_Checklist.md`, `docs/client-api.md` |

**Контрольные доказательства к моменту подготовки отчёта:**
- Baseline exact `def405ffc...`: исходный независимый probe **P1 CONFIRMED**, **500 → 200** и upstream POST **1 → 2** без разрешённого reconciliation.
- RED single-layer `fb7ca961...`: [backend 45036473916](https://github.com/nikamurkaa/sain-hack-2026-4Sain/actions/runs/45036473916), **3 failed / 311 passed**. Следовательно, простого завершения Room journal недостаточно.
- GREEN code checkpoint `bfff9048c85340f63451bf2c5b373e65eb5ef8e7`: [backend 45037464859](https://github.com/nikamurkaa/sain-hack-2026-4Sain/actions/runs/45037464859) **330 pytest**; [frontend 45037464823](https://github.com/nikamurkaa/sain-hack-2026-4Sain/actions/runs/45037464823) **43 Chromium + 43 Firefox**; [Windows 45037464825](https://github.com/nikamurkaa/sain-hack-2026-4Sain/actions/runs/45037464825) **SUCCESS**. Independent 19 Python cancellation cases verified in extracted exact GitHub Windows ZIP; additionally independently re-run provided API probe adapted to **positive** assertions: first response HTTP500/transport loss, same-key 409, old-time 409 before/after GET, upstream POST exactly 1 before authorized new T2 action and 2 only after explicit T2.
- Additional `asyncio.Task.cancel()`/double-cancel test appended on checkpoint `2d22164094f33e18efbc861166eaa6d8ec9b15f5`; **the newest backend CI must independently prove it**, not assume prior 330 count covers it.
- **Final exact-HEAD three-success gate:** the docs commit necessarily changes SHA; find the final exact SHA and backend/frontend/Windows completed SUCCESS runs **in PR №20 description after verification**. Earlier green results cannot be used as final-head evidence.

**Test matrix (non-exhaustive):** cancellation before first GET, before first POST, after first accepted POST, before/after read-back GET, before second POST, after second accepted POST, after final GET, multiple commands, repeated/mismatched Idempotency-Key, both message/manual endpoints, new T1 write forbidden, T2 write after recovery allowed, failed/repeated GET, unrelated virtual preview, two guests, token expiry, midnight, invalid UTC offset, direct `Task.cancel()` and second cancellation, lock release, no orphan background work. Existing MR-001–MR-004 and MR-NEW-01–03 backend/frontend tests also remain part of full CI.

## 7. Accepted architectural restrictions and backlog

**Stage 1 prototype ONLY:** single-process, single-worker, one in-process owner per Room, bounded in-memory operation journal, new synthetic session after restart. No crash- or host-failure durability, no distributed lock, no official upstream reattach/receipt or external exactly-once promise. Cancellation after accepted upstream POST is still observationally `uncertain` even when subsequent GET shows expected settings. Native Windows START/STOP, physical screen reader/mobile OS keyboard/real touch, full historic Git blobs secrets audit, organizer API/LLM/STT and brand/IP permissions are NOT TESTED/approved. Physical R6 with stay less than 15 minutes cannot be fulfilled and is not falsely scored compliant.

**Explicitly deferred, not merged into this P1 fix:**
- **MR-NEW-05 · P2 mobile UX:** critical notice leaves viewport after focus on blocked composer at 320×568; Stage 4 compact anchored summary/return-to-recovery affordance.
- **Desktop decorative AI orb cropping** and fake phone status bar hierarchy; Stage 4 visual polish.
- **Stage 6 durable persistence** (authorized local SQLite/WAL, restart/session restore, crash-recovery model); not implied by this in-memory correction.
- **Native Windows runtime acceptance** and **physical accessibility QA** (TalkBack/VoiceOver, touch and OS keyboard) for appropriate later release gates.

## 8. Safe rollback and independent signoff

Only normal (non-force) revert commits on `integration/stage1-foundation-acceptance`, preserve all previous source PRs #14–19 and historic tag, then rerun entire exact-head CI. Never silently repeat unsafe upstream POST to escape unknown outcome. Scope explicitly excludes any merge into main, production deploy, official organizer tokens or closed `/run`, external expert contact and Stage 2 development.

**Target status after three final-head CI checks: READY FOR TARGETED INDEPENDENT RE-REVIEW.** Neither author nor green GitHub Actions can self-issue `APPROVED FOR MERGE`; reviewer and owner act separately.
