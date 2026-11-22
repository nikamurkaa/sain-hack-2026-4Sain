# SAIN Stage 1 — Final Temporal Recovery Remediation (MR-NEW-01/02/03)

**22 ноября 2026 · команда 4Sain · [Draft PR №20](https://github.com/nikamurkaa/sain-hack-2026-4Sain/pull/20) · Stage 1 only.**

**Решение по независимому отчёту** `SAIN_Stage1_Final_Independent_ReReview(2).md` (отдельно предоставленный независимый отчёт, не файл репозитория): исходный повторный вердикт `REQUEST CHANGES BEFORE MERGE` верен для `fb3b082d0a457be10a462c468c565147bcedb423`. Исполнитель исправил подтверждённый P1 MR-NEW-01 и оба P2 MR-NEW-02/03. **Это не независимый APPROVE и не разрешение на merge.** Новый точный integration HEAD сверяется по актуальному [PR №20](https://github.com/nikamurkaa/sain-hack-2026-4Sain/pull/20); документационный коммит не может заранее содержать свой собственный SHA. Exact-HEAD backend/frontend/Windows run IDs для финального коммита закрепляются в описании PR после их успешного завершения. Проверенный преддокументационный код: `53b96202fa5ef4a1b2d265c86e42d1d1763daf52`.

## 1. Root cause и исходный RED

**MR-NEW-01 · P1:** `main.py` сохранял `session.at` только после полноценного `done`; частичное действие в T2 оставляло его на T1. `GET /state` без параметров читал T1, а React `refreshActual()` ошибочно принимал любой HTTP 200 за подтверждение partial в T2. Следующий POST с `at=T1` проходил проверку `session.at`, хотя upstream уже получил изменение в T2. Тесты предыдущего этапа делали `attempt.at == session.at` и не выявили дефект.

**RED:** независимо написан `tests/stage1/test_mr_new01_temporal.py` и помещён в отдельный коммит [9eda085](https://github.com/nikamurkaa/sain-hack-2026-4Sain/commit/9eda085cb09e9678fba00b036c178e99e8cbc613). [GitHub Actions #45031450797](https://github.com/nikamurkaa/sain-hack-2026-4Sain/actions/runs/45031450797): `2 failed, 305 passed`; оба падения при отсутствии `attempted_at`/temporal contract. Настоящий локальный FastAPI+MockTransport самостоятельно подтвердил исходную последовательность: T1=2026-11-12T20:00+03, свет=70%; POST compound в T2=20:45, подтверждён light=0%, sound отвергнут; HTTP409 ACTION_PARTIAL; GET default T1=70%, GET ?at=T2=0%; новая команда в T1 исходно была HTTP200 (недопустимо).

## 2. Три разных времени и строгая серверная семантика

| Величина | Хранение | Значение |
|---|---|---|
| **Последний успешный диалог** | `ClientSession.at` | Продвигается **только после полного успешного ответа**. Partial/uncertain/conflict не создают `done` и не меняют эту дату. |
| **Граница потенциально применённого действия** | `ClientSession.mutation_floor` | Монотонный UTC instant; при `ActionFailure` с реальным POST учитывается T2 даже при потере ответа. Защищает и `/messages`, и `/devices` от более раннего write. |
| **Время попытки и evidence** | `Room.operations[operation_id].attempted_at`, `ClientSession.action_issues[operation_id]` | Источник — доверенная проверенная сервером дата запроса. Кешируются статус, подтверждённые устройства, флаг проверенности; после GET хранится подтверждённый снимок. Никаких токенов, речи или PII в журнале. |

**Протокол:**

1. `POST /api/v1/messages` либо `POST /api/v1/devices` валидирует IANA время, Idempotency-Key и порядок. `Room.execute` ставит `mutation_possible` непосредственно перед действительным отправлением POST; повтор POST после потерянного ответа **не выполняется**.
2. На `ACTION_PARTIAL` / `ACTION_UNCERTAIN` / `ACTION_CONFLICT` backend отдаёт `code`, `message`, `operation_id`, `confirmed_devices`, **`attempted_at`**. Значение берётся из validated operation/session, не из произвольного frontend query.
3. Незавершённый результат блокирует **все новые изменяющие команды** с новым ключом кодом `RECOVERY_REQUIRED` (409); предыдущий Idempotency-Key воспроизводит тот же сохранённый 409 без нового upstream POST.
4. Авторизованный **`GET /api/v1/reconciliation?operation_id=...`** читает upstream через `Room.state(attempted_at)`, проверяет ранее подтверждённые устройства по предыдущему `Room.operations[operation_id].state`, возвращает `operation_id`, `attempted_at`, `status`, `confirmed_devices`, `verified=true`, `snapshot.at`, `snapshot.state`, `next_action_at`. Изменение **только локального** флага сверки и монотонного `last_confirmed`; GET **никогда не отправляет POST/action**. Отказ GET/конфликт подтверждённых устройств сохраняет недостоверность и блокировку.
5. После успешного GET новая команда разрешена только на `at >= max(session.at,mutation_floor)` по реальному UTC времени. `session.at` остаётся временем последнего успешного сообщения, `next_action_at` задаёт безопасную дату новой команды.
6. Обычный `GET /state?at=...` продолжает быть read-only preview; он **не** разрешает recovery, не снимает блокировку, не меняет `last_confirmed`. Обычный GET в старое T1 не может откатить T2 после успешной сверки.
7. Для definitive upstream rejection 429/закрытого сеанса сохраняются существующие status/codes и side-effect semantics. Не вводится автоматическое exactly-once, distributed lock или SQLite.

**Ограничение доказательства:** `verified=true` означает наблюдённый снимок симулятора в попытанном UTC instant с проверкой **известных** подтверждённых устройств; это **не** означает, что все действия выполнены, что потерянный POST точно не был применён или что upstream атомарен. При status=`uncertain` классификация остаётся uncertain даже после чтения snapshot.

## 3. Frontend temporal oracle и race isolation

`ActionApiError.attemptedAt` валидируется как ISO datetime с явным UTC offset. `verifiedReconciliation(issue,payload)` не принимает HTTP200 без совпадающих `operation_id`, `status`, списка подтверждённых устройств, `attempted_at`, `snapshot.at`, допустимого `snapshot.state` и `next_action_at`. Сравнение происходит через UTC milliseconds (`Date.parse`); одинаковый момент с `+03:00` и `Z` допустим, старый 20:00 или invalid timestamp — нет. Только после успешной проверки выставляется `issue.checked=true`, обновляется UI фактическим state и разрешается новая сознательная команда в `next_action_at`.

Каждый recovery запрос связан с `operation_id` и `recoveryRevision`; устаревшие/out-of-order ответы, смена токена и unmount (`AbortController`) не заменяют новый снимок. GET failure оставляет stale=TRUE и блокировку, кнопка повторного GET не вызывает POST. При reconnect server `pending_action` позволяет восстановить незавершённое уведомление внутри того же токена. Session expiration обрабатывается отдельно, final read-only не меняется.

## 4. MR-NEW-02 / MR-NEW-03: действия и визуальный результат

**MR-NEW-02 (P2):** `canSubmit` в `main.tsx` используется **одинаково** для desktop и `MobileStay`, учитывая allowed, read-only, expiry, busy, pending, draft и pending recovery. На 320×568 с непустым draft при сбое GET: disabled и `aria-describedby=sain-action-hint`, нет POST; после второго успешного GET кнопка включается, текст не отправляется автоматически. Дополнительно в `design/layout.css` затемнён декоративный Figma-circle, иначе HTML disabled не менял визуально оранжевую SVG-подложку.

**MR-NEW-03 (P2):** прежнее absolute/z-index overlay закрывало alarm/DND. Панель помещена **в normal document flow** перед Figma frame только при активной ошибке, с кнопками не менее 44 CSS px и видимым статусом. Прокрутка и Tab/Enter открывают оба действия на низкой высоте. После GET→dismiss все шесть устройств видны в исходном дизайн-слое. Проверены Playwright viewport **320×568, 360×640, 375×667, 375×812, 390×844, 430×932, 768×1024, 1440×900**, CSS zoom 200%; keyboard focus; нет horizontal overflow. Реальная экранная клавиатура, physical screen reader и нативный touch-экран **не тестировались**, поэтому WCAG AA или hardware accessibility не заявлены.

## 5. Regression matrix

| ID | Severity | Before | Fix | Regressions & artifacts | Status исполнения |
|---|---|---|---|---|---|
| **MR-NEW-01** | P1 | T2 effect + T1 confirmed UI + небезопасный T1 POST | `attempted_at`, floor+issue journal, auth GET reconciliation, strict UTC+op validator, no blind POST | `test_mr_new01_temporal.py`; `stage1-temporal.test.ts`; `stage1-temporal.spec.ts`: T1/T2; 20:45 light=0; forbidden earlier message/manual POST; midnight; equal-at; lost GET; uncertain manual; conflict; repeat keys; two guest isolation; final read-only inherited; old/malformed/offset-mismatched snapshot; stale response. | **Implemented; independent final review pending** |
| **MR-NEW-02** | P2 | Mobile send выглядел активным при stale issue + nonempty draft | Shared `canSubmit`, aria hint и видимо приглушённый Figma send button | E2E `MR-NEW-02` с 320×568 screenshot и проверкой 0 auto-POST до и после GET | **Implemented; independent final review pending** |
| **MR-NEW-03** | P2 | Overlay закрывал будильник и DND, низкие экраны не доказаны | In-flow alert, responsive scroll, 44px targets, исходные cards сохраняются | E2E 8 viewports × 2 browsers, 200% zoom, tab/enter, GET→dismiss→6 devices, `browser-screens` artifacts | **Implemented; independent final review pending** |
| **WIN-ORACLE** | P2 test packaging | ZIP flat root: 304 passed + один неверный source-only file path test | `test_quality_gate_time_ops.py` принимает строго два документированных layout: source `windows/` и Windows package `BUILD_INFO.txt` + root launch scripts | Независимый локальный полный pytest **311 passed** из **неизменённого** b97 ZIP без symlink/копий и offline 10/60. Release не содержит дубликатов launch scripts. | **Implemented; package-native Windows launch still NOT tested** |

### RED→GREEN / CI provenance

- **RED baseline:** [45031450797](https://github.com/nikamurkaa/sain-hack-2026-4Sain/actions/runs/45031450797), test commit `9eda085cb09e9678fba00b036c178e99e8cbc613`: **2 failed**, 305 passed. Правильная причина — отсутствующий temporal contract, а не искусственная ошибка импортов.
- **GREEN code checkpoint** [backend 45032271808](https://github.com/nikamurkaa/sain-hack-2026-4Sain/actions/runs/45032271808), [frontend 45032271827](https://github.com/nikamurkaa/sain-hack-2026-4Sain/actions/runs/45032271827), [Windows 45032271793](https://github.com/nikamurkaa/sain-hack-2026-4Sain/actions/runs/45032271793) на `b97cd5148a98d876778ae060244ca284e162f3be`: backend **311 pytest**, 2× offline 10/60, Chromium **41/41**, Firefox **41/41**, Node **13/13**, TS/Vite pass; screenshots 8 viewport/2 browsers [artifact 14757812883](https://github.com/nikamurkaa/sain-hack-2026-4Sain/actions/runs/45032271827/artifacts/14757812883). Дальнейшая визуальная коррекция затемнённой кнопки добавляет код на `53b96202fa5ef4a1b2d265c86e42d1d1763daf52` и требует **ещё один exact-final-HEAD прогон**.
- **Final CI links/HEAD:** после этого документационного коммита см. обновлённое описание Draft PR №20. Прежние green-шары не считаются доказательством новой версии; три workflow обязаны иметь один настоящий checkout SHA.
- **Локально независимо:** Windows release ZIP контрольного `b97cd5...` извлечён целиком без изменения файлов и без symlink; `python -m pytest -q` → **311 passed**, `python -m scripts.check_offline` → **10/60**, `incorrect_requests=[]`, `failed_rules={}`, `extra_changes=0`, `C=S=x=1.0`. Native Windows не запускался.

## 6. Изменённые файлы и ограничения

**Backend:** `backend/room.py`, `main.py`, `backend/api_models.py`, `frontend/serve.py`. **Frontend:** `frontend/src/api.ts`, `actionFeedback.ts`, `temporalRecovery.ts` (новый), `main.tsx`, `model.ts`, `ActionNotice.tsx`, `design/MobileStay.tsx`, `design/layout.css`. **Tests:** `tests/stage1/test_mr_new01_temporal.py` (новый), `tests/test_quality_gate_time_ops.py`, `frontend/tests/stage1-temporal.test.ts` и `stage1-temporal.spec.ts` (новые), `stage1-action-error.test.ts`.

**Документация:** `docs/client-api.md` и существующие Stage 1 интеграционные отчёты/матрицы/checklists; этот документ.

**Ограничения:** один процесс, один worker, in-memory operation/session journal, fresh synthetic session on restart, no remote authoritative receipt/re-attach, no exactly-once, no official closed API test; R6 <15 минут физически невозможен; legacy tag, original PRs and main неизменны; исторический секретный audit и внешние разрешения на SAIN/IP не завершены. Windows native START/STOP, реальная мобильная клавиатура и настоящий screen reader — **NOT TESTED**.

**Rollback:** исключительно обычным отдельным non-force revert коммитом в интеграционной ветке, без изменения main, с полным повтором exact-HEAD CI. Не replay неизвестных POST и не считать старый snapshot подтверждением T2. Независимый reviewer должен проверить исходный reproducer, новый API-контракт, Playwright screenshot и самостоятельно решить merge gate. **Исполнитель не выдаёт APPROVED FOR MERGE.**
