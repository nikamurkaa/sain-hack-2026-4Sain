# SAIN Stage 1 — MR-NEW-06 Frontend Error Recovery Remediation

**Дата:** 22 ноября 2026 · **PR:** [#20 — integration/stage1-foundation-acceptance](https://github.com/nikamurkaa/sain-hack-2026-4Sain/pull/20) · **Базовый дефектный SHA:** `d9f3b8ec7a78b9c83edd09cce541bc3cdfd7c47f`. Исходный независимый аудит: `SAIN_Stage1_MRNEW04_Independent_ReReview(2).md` и `SAIN_Stage1_MRNEW04_Independent_Evidence(2).zip` (включая `evidence/mrnew04_frontend_422_retry_probe.py`, `mrnew04_frontend_422_retry.log`).

**Merge-контроль:** документ служит доказательством исправлений, **не** выдаёт independent APPROVED или разрешения на merge. Фактический HEAD документационного коммита и ссылки на его три exact-SHA GitHub Actions указываются в описании Draft PR #20 **после** завершения этих трёх workflows; более ранний кодовый SHA не заменяет последнего HEAD.

## 1. Реальный MR-NEW-06 / P1 и RED

Независимый Chromium/React + настоящий loopback FastAPI probe изменил только **первое тело POST** в HTTP bridge: UI послал `text="Сделай попрохладнее"`, реальный FastAPI/Pydantic получил `text=""` и отклонил запрос **HTTP 422 до входа в обработчик**. `/session` сразу подтвердил `reconciliation_required=false`, `pending_action=null`, не было новых upstream POST. Но старый frontend пометил исход как возможный потерянный POST, выставил `unansweredPost=true`, оставил ввод, заблокировал отправку и показал кликабельное «Повторить», не делающее запрос. Исходный лог: `retry_visible=True`, `click_emitted_no_post=True`, `frontend_send_disabled=True`.

**Независимая красная регрессия:** новый `frontend/tests/stage1-definitive-rejection.spec.ts` внесён отдельным коммитом [eeb59f9](https://github.com/nikamurkaa/sain-hack-2026-4Sain/commit/eeb59f94f383fa45bb3c5302ffb8b80b15d1f5b7) **до продуктивных исправлений**; [frontend RED #45041086124](https://github.com/nikamurkaa/sain-hack-2026-4Sain/actions/runs/45041086124): **3 failed**, Chromium 320×568 / 375×812 / 1440×900, **43 старых passed**. Реальный FastAPI ответил `422`, old UI отобразил «Ответ команды не получен. Проверяем… Повторить». Это функциональная неисправность после определённого отказа, не ошибка тестовой заглушки.

## 2. Первопричина

`frontend/src/main.tsx` направлял *любую* не-`ActionApiError` ошибку POST (включая известный Pydantic 422) в `recoverUnansweredPost`, сохранявший `unansweredPost=true` до подтверждения возможного действия. Когда `/session` справедливо не сообщал pending или done, UI оставался заблокированным навсегда. Старая Figma mobile error card выводила «Повторить» при неподтверждённой blocked-сессии, но её handler `send()` возвращался без POST. Проблему нельзя решить правилом «все 4xx/422 безопасны»: `ActionFailure`, `RECOVERY_REQUIRED`, транспортные 5xx и произвольный JSON не являются доказательствами отсутствия upstream effects.

## 3. Минимальный доказуемый API-контракт

Backend `main.py` теперь помечает **только точно подтверждённые side-effect-free отказы для двух изменяющих маршрутов** ответным заголовком `X-Sain-Rejection-Class`:

- `prehandler` — только `RequestValidationError` FastAPI/Pydantic из `POST /api/v1/messages` или `POST /api/v1/devices`, когда обработчик не запускался; оригинальные HTTP 422 body/status и набор ошибок сохраняются.
- `domain` — только HTTP422 ServiceError c документированными кодами `INVALID_TIME` для messages/devices и `INVALID_VALUE` для devices, которые формируются **до upstream POST**; ошибка с иным кодом не помечается.
- Для `ACTION_PARTIAL`, `ACTION_UNCERTAIN`, других 409, 401/403, 429, 500/502, таймаутов и неразобранного JSON подтверждения **нет**.

Локальный `frontend/serve.py` теперь передаёт этот заголовок **только при 422, только для этих POST-маршрутов, только с двумя разрешёнными значениями**. Отсутствие проксирования было обнаружено в первом GREEN-попытке: FastAPI давал маркер, а браузер его не видел; старый fail-closed путь сохранялся. Изменение не ослабляет прокси и не отражает произвольные заголовки.

`frontend/src/api.ts` добавляет тип `DefinitiveApiError`, `DefinitiveRejectionKind`, `failureCategory`; при обработке `prehandler` проверяет структурное `detail[]` Pydantic (типы, source loc, bounded size), при `domain` проверяет `status="error"` и allowlisted `code`, конкретный endpoint. **HTTP422 без маркера, маркер с невалидным body, 409 с таким маркером или фальшивый неизвестный код остаются недостоверными.** Секреты, raw traceback и сообщения от непроверенного JSON не выводятся.

## 4. Матрица решений API

| Категория | Требуется ли reconciliation | Draft / возможность следующего POST | Retry и Idempotency-Key |
|---|---|---|---|
| Certified FastAPI 422 `prehandler` | **Нет для данного POST**, но `GET /session` проверяет другие pending операции | Draft сохраняется; после `session.reconciliation_required=false` и отсутствии текущего issue разблокировать | Нет автоповтора и старого-key retry; редактирование → **новый** ключ |
| Certified `INVALID_TIME` / `INVALID_VALUE` 422 `domain` | Аналогично: доказуемый отказ до upstream POST | Показывать русское сообщение, сохранять редактируемый draft; другие pending остаются заблокированными | Новый ключ после сознательной правки |
| HTTP 200 `response_class=refused` | Это подтверждённый ответ, а не потерянная доставка; без `done` | Показывать доменный отказ, последующий ввод доступен по обычному контракту | Новая команда — новый ключ |
| `ACTION_PARTIAL`, `ACTION_UNCERTAIN`, `ACTION_CONFLICT`, `ACTION_FAILED` 409 | **Да**, только точный `operation_id`/UTC `attempted_at`, подтверждённые устройства | До валидной сверки заблокировать; не заявлять `done` | Исходный ключ только для cached status; новых POST без проверки нет |
| `RECOVERY_REQUIRED`, `TIME_BACKWARDS` 409 | Сохранять защитную временную границу; проверять `/session` и pending при необходимости | Не обходить floor сменой ключа/endpoint | Никакого слепого retry |
| `IDEMPOTENCY_CONFLICT` 409 | Не доказывает отсутствие старой операции, поэтому нельзя автоматически разблокировать | Сверить серверный сеанс; прежние проблемы не игнорировать | Изменённый payload запрещён со старым ключом |
| 401 / 403 | Авторизация или права должны быть восстановлены; не считать отказом от принятого POST | 401 → завершение токена; 403 → блокировка/уточнение прав | Не повторять POST автоматически |
| 429, неизвестный 4xx, 500/502, timeout/abort, malformed JSON | **Исход не доказан**, `/session` → pending ID → только GET reconciliation; не принимать HTTP200 чужого момента | `unansweredPost`, stale и disabled, пока нет подтверждённого восстановления | Никакого авто-POST; повтор при неизвестном исходе запрещён |

**При сетевой ошибке `GET /session` после сертифицированного 422** разблокирование не выполняется: сообщение объясняет, что требуется проверка доступности сеанса. Сертификат касается только **текущего** POST, не конкурирующих операций в той же сессии.

## 5. Изменения React/UX

`send()` и `applySetting()` используют общий `handleDefinitiveRejection(error)`: устраняют pending для действительно отвергнутой попытки, оставляют ввод, показывают исправимое сообщение, временно сохраняют blocked до авторизованного `GET /session`, проверяют `reconciliation_required` и `pending_action`, при наличии другого unresolved issue переходят в существующий op-based recovery. Только после подтверждённо чистого сеанса снимают *эту* блокировку. Никакой POST не генерируется внутри обработчика ошибок. Изменённый текст отправляется только при новом клике, создающем новый `crypto.randomUUID()`.

`MobileStay` и desktop chat больше не предлагают ложную кнопку «Повторить», когда действие запрещено либо нет действительной replayable попытки. Декоративная мобильная надпись Retry убирается вместе с кликабельной Hit-областью; доступные send/keyboard/ARIA состояния из MR-NEW-02 сохранены. Дизайн-система SAIN не перерабатывалась. Ошибка не превращается в `done` и не удаляет предыдущие confirmed effects.

## 6. Проверки RED→GREEN и regression oracle

- **RED** `eeb59f94...`: [frontend #45041086124](https://github.com/nikamurkaa/sain-hack-2026-4Sain/actions/runs/45041086124): 3 new failures на реальном Pydantic 422; старые 43 Chromium прошли.
- **GREEN подтверждённый code checkpoint** `539661f914541e7ac7f739165bf2244f316b395a`: [backend #45041721017](https://github.com/nikamurkaa/sain-hack-2026-4Sain/actions/runs/45041721017) — 334 Python; [frontend #45041721061](https://github.com/nikamurkaa/sain-hack-2026-4Sain/actions/runs/45041721061) — **17 Node**, TypeScript/Vite, **46 Chromium + 46 Firefox**; [Windows #45041721025](https://github.com/nikamurkaa/sain-hack-2026-4Sain/actions/runs/45041721025) — packaged successfully. Это **не** финальный SHA после документации.
- Пояснение intermediate-RED: до фикса `frontend/serve.py` оставался скрытый барьер: FastAPI вернул маркер, но прокси удалял его. Проверка ref `2dc1c15...` с кодом React и backend без прокси-маркера всё ещё падала — реальный интеграционный тест выявил этот контрактный дефект.
- **Browser REAL FastAPI**: `frontend/tests/stage1-definitive-rejection.spec.ts` (320×568, 375×812, 1440×900 × Chromium/Firefox) подменяет body **только первого** POST, получает real HTTP422, подтверждает `/session pending=null`, unchanged room state / no history / один HTTP запрос, показывает ошибку, сохраняет/правит draft, подтверждает enabled send / hidden misleading Retry, выполняет **второй явный POST с другим ключом** → HTTP200 `done`, state changed, 1 history entry. Дополнительно отдельный ручной device API/browser сценарий: invalid `values={}` → no upstream mutation, пользователь явно повторно сохраняет valid climate через новый key. Тесты не заменены простыми HTML checks.
- **Backend TestClient / real MockSimulator**: `tests/stage1/test_mr_new06_definitive.py` проверяет сертификат FastAPI/доменных отказов, отсутствие effects, отдельные новые ключи и настоящие POST; `ACTION_PARTIAL`/неразрешённая temporal операция НЕ имеют safe marker.
- **Node error matrix**: `frontend/tests/stage1-definitive-rejection.test.ts` проверяет сертифицированный/неподтверждённый HTTP422, malformed JSON/headers, domain refusal, ACTION_*, 401/403/409, 429, 500/502, timeout/abort, unknown; границы `DefinitiveApiError` строго ограничены.
- **MR-NEW-04 regression**: существующие `tests/stage1/test_mr_new04_{cancellation,matrix}.py` и `frontend/tests/stage1-cancellation.spec.ts` включены в полный suite. T2=20:45 cancelled accepted light POST, same key replay не делает нового upstream POST, GET сверяет тот же op/time, T1 до и после запрещён, следующий write только T2+ после recovery. Отсутствие сертификата безопасного отказа для `ACTION_UNCERTAIN` отдельно проверяется.
- **Final exact-head CI:** абсолютный SHA, backend/frontend/Windows ссылки и screenshot archive указаны в **текущем описании Draft PR #20**, только после трёх completed SUCCESS по *одному* HEAD, а не подменены кодовым checkpoint.

## 7. Изменённые файлы

`main.py` (серверные сертификаты), `frontend/serve.py` (узкий allowlist проксирования), `frontend/src/api.ts` (типизированная модель), `frontend/src/main.tsx` (два action handlers), `frontend/src/design/MobileStay.tsx` (no dead retry), новые `frontend/tests/stage1-definitive-rejection.spec.ts`, `frontend/tests/stage1-definitive-rejection.test.ts`, `tests/stage1/test_mr_new06_definitive.py`. Отчёт и существующие Stage 1 docs обновлены.

## 8. Остаточные риски и безопасный откат

Только один процесс/worker и in-memory session/Room operations; при рестарте токены/операции теряются, нет гарантированной внешней квитанции или exactly-once, нельзя утверждать production multi-worker reliability. MR-NEW-05 P2 (recovery notice вне viewport после фокуса на 320px), декоративный AI orb, мобильный fake status-bar (Stage 4); Stage 6 durable storage; native Windows START/STOP и физический screen reader/touch/OS keyboard — отложены без фиктивного PASS. Доступ к официальному API, закрытому `/run`, production, историческому тегу не использован.

**Rollback:** безопасный `git revert` обычными non-force коммитами *только* в integration branch и новый полный exact-head gate; не изменять main и не выполнять повтор uncertain upstream POST ради восстановления. На откате возвращается исходный MR-NEW-06 P1, поэтому rollback не эквивалентен разрешению merge.

**Возможный финальный технический вердикт после exact-head checks:** `READY FOR FINAL TARGETED RE-REVIEW`. Это не independent APPROVED и не разрешение владельца на merge.
