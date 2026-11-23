# SAIN Smart Room — Stage 4 Phase 2: Visual Acceptance

**Scope:** Stage 4 branch `stage4/premium-ui-ux`, PR #26, issue #25. Base `main`: `3c240169cc858c6df820d513b02e8f462a0ecd14`. Stage 4 Phase 1 baseline: `1a7fff41ceb2759ac582acee5e1f3fef413182fc`. Updated 2026-11-23.

## Reference hierarchy

1. The **29 supplied Figma contact-sheet images** and exact checked-in `frontend/src/design/frames.json` plus `art-01.svg`…`art-29.svg` define the legacy visual frame.
2. The **React source** (`MobileStay.tsx`, `Layout.tsx`, `views.tsx`, `Voice.tsx`, `SpeechReply.tsx`, `main.tsx`) is the authority for working behavior and accessibility.
3. GitHub Actions **Playwright browser PNG files** constitute actual rendered proof. Baseline browser evidence is available from the successful Phase 1 run [45232995273](https://github.com/nikamurkaa/sain-hack-2026-4Sain/actions/runs/45232995273); later runs must be checked by exact head SHA.
4. Live Figma MCP returned a **Starter-plan call-limit error**. Current design-file pixel parity is **NOT VERIFIED**; do not claim pixel-perfect against latest live Figma.
5. Live Bifrost, real STT/TTS, and organizer dev tokens **NOT TESTED**.

## All 29 screens — source, actual controls, states and evidence

The "visual review" column lists intended acceptance checks, not an unearned pass verdict. These checks should be applied in the stated viewport matrix for each reachable state.

| # | Exported screen | React ownership | Actual interaction | State / invariant | Visual review | Browser / test evidence |
|---|---|---|---|---|---|---|
| 01 | План · Утро | MobileStay · plan / morning | Периоды; переход «В номер»; разъяснение план/факт | План и R6-уведомления | Таймлайн и подписи, предупреждения без скрытия | screens.spec.ts period + stage4-ux R6 |
| 02 | Мой номер · Утро | MobileStay · room / morning | Меню; устройства при разрешённом управлении; Диалог | Подтверждённый snapshot и read-only | Лейблы и достижимость на узком экране | screens.spec.ts period + responsive |
| 03 | План · День | MobileStay · plan / day | Переключение периода; переход | План/отдельный GET actual | Верная типографика и плановые предупреждения | screens.spec.ts period |
| 04 | Мой номер · День | MobileStay · room / day | Навигация, карточки устройств | Device state only from snapshot | Полосы состояния, подписи без обрезки | screens.spec.ts period |
| 05 | План · Вечер | MobileStay · plan / evening | Периоды, сценарий | R1/R8 explanation and R6 when warning | Контраст вечернего акцента/таймлайна | screens.spec.ts period |
| 06 | Мой номер · Вечер | MobileStay · room / evening | Устройства, голосовой путь через chat | Подтверждённое состояние | Читаемость названий звуков | screens.spec.ts period |
| 07 | План · Сон | MobileStay · plan / night | Периоды; «В номер» | Ночь и разъяснения | Свет/шторы — план vs факт | screens.spec.ts period |
| 08 | Мой номер · Сон | MobileStay · room / night | Устройства, история | Read-only / управляемый режим | Контраст и выключенные элементы | screens.spec.ts period |
| 09 | Диалог · подсказка | MobileStay · chat / empty | Suggestion, input, mic, menu | Запрет send при unknown POST | 320×568 fixed composer, орб и hit targets | stage4-ux, responsive, journey |
| 10 | Диалог · ответ | MobileStay · chat / one response | History dialog; TTS через SpeechReply | Done only after server receipt | Длинные ответы, очередь focus и scroll | screens.spec.ts, quality-history, speech tests |
| 11 | Начало заселения | MobileStay · welcome | Заселиться, меню | Данные/план предварительные | Логичная CTA и читаемость вводной карточки | screens.spec.ts, journey |
| 12 | Голосовой ввод · запись | Voice · record/start | Остановить запись; отмена | Mic permission / 5MB/30s | Ясный статус записи; aria-live | journey voice, voice lifecycle |
| 13 | Голосовой ввод · STT | Voice · wait | Отмена; нет повторной отправки | С ожиданием AbortSignal | Распознавание ≠ выполненная команда | journey voice |
| 14 | Голосовой ввод · текст | Voice · review | Редактирование transcript; отправка | Пустой текст запрещён | Различать проверку и успешное действие | journey voice |
| 15 | Диалог · отказ | MobileStay · chat / first refused | История, composer | Reply refused, нет успешного state | Полный текст причины отказа | screens.spec.ts refusal |
| 16 | Диалог · ошибка | MobileStay · chat / first error | Закрыть, условный safe retry | Не повторять неопределённый POST | Компактная семантическая error-card | stage4-ux error + screens |
| 17 | Виртуальное время · Утро | MobileStay · virtual/morning | Только переключение чтения | GET preview; период доступности | Нет управления из preview | screens.spec.ts + responsive |
| 18 | Виртуальное время · День | MobileStay · virtual/day | Только GET | Без изменения snapshot | Подписи/контраст временной шкалы | screens.spec.ts |
| 19 | Виртуальное время · Вечер | MobileStay · virtual/evening | Только GET | Истинное virtual at | Контраст на тёплой иллюстрации | screens.spec.ts |
| 20 | Виртуальное время · Ночь | MobileStay · virtual/night | Только GET | Unavailable state | Читаемость выключенного режима | screens.spec.ts |
| 21 | Климат | Settings · climate | Input number; -/+; Save | Draft preview; server-ack success | Степпер, крупный градус, ясный preview | stage4-ux climate |
| 22 | Будильник | Settings · alarm | Input time; select mode; Save, cancel if exists | Повтор симулятором не поддержан | Никакой fake toggle, time hint, запрет пустого | stage4-ux alarm |
| 23 | Звук | Settings · sound | Select track; volume; Save | Track/volume по catalog | Полные названия/возможность выбрать трек | quality-tracks, screens.spec.ts |
| 24 | Загрузка | main · loading | Смена сеанса | Скелетоны, статус загрузки | Не обозначать пустой placeholder как реальную кнопку | screens.spec.ts |
| 25 | Отправка просьбы | MobileStay · chat / pending | Команды блокируются | In-flight POST; idempotency | Индикатор ожидания, поля недоступны | quality-history, stage1 tests |
| 26 | Успех | MobileStay · chat / done | История, TTS | Только подтверждённый reply/state | Статус и согласованность текста/состояния | screens.spec.ts |
| 27 | Отказ после истории | MobileStay · chat / refused | История, composer | Не выдавать отказ за успех | Читаемость длинного отказа | screens.spec.ts |
| 28 | Ошибка после истории | MobileStay · chat / error | Закрыть, допустимый retry | Сверка до следующего POST | Без фиктивного Retry и пустых 205px | stage4-ux, quality-history |
| 29 | Истечение сеанса | main · expired | Переподключение / новый сеанс | Никакой утечки между гостями | Понятные и доступные CTA | screens.spec.ts, stage1 identity |

## Priority changes applied in Phase 2

- Error cards: compact visual hierarchy; actual failure text, uncertainty consequences, and conditionally permitted actions. **No automatic duplicate POST**.
- Climate: current vs proposed settings text and proper range validation. **No unconfirmed success**.
- Alarm: unavailable repeat is static information, not a fake toggle; time/signal are real inputs; separate state hint from cancel.
- Voice: state announcements for permission/start/record/wait/review/error, empty STT treated as error; Stage 3 stale-play lifetime remains unchanged.
- Mobile: 320×568 fixed safe composer, touch targets, focus visibility. 375×812 Figma art remains recognisable.
- Desktop: quiet, spacious three-column hotel layout with restrained copper surfaces, not a cloned phone frame.

## Mandatory viewports and assertions

`320×568`, `375×812`, `390×844`, `768×1024`, `1024×768`, `1440×900`, `1905×911`, `1920×1080`.

The responsive test enforces viewport width and horizontal overflow, checks header Menu pointer hit-testing (minimum 24px bounding box and center not obscured), tests priority chat input readability and presence, and checks keyboard navigation / 200% zoom access. Screenshots remain source-of-truth for color, overlaps, text hierarchy and Figma fidelity that numeric tests cannot determine by themselves.

## Reviewer acceptance criteria

- Production build, TypeScript and all Node tests pass.
- Chromium and Firefox Playwright pass **on one final PR HEAD**; Python offline and Windows workflows also green on the identical SHA.
- Each of 29 exported states has a relevant screenshot and behavior path verified in a running application; comparative screenshots from actual browser runs only.
- No current confirmed P0/P1 visual/functional issues, no unreadable critical text or unclickable reachable controls.
- Confirmed warning/error and read-only invariants; no fake success on incomplete request.
- Keyboard-only and meaningful announcements assessed. Automatic checks alone do **not** establish WCAG conformance.
- Independent visual acceptance remains a separate owner/reviewer decision; a green build alone does not imply approval.

## Not tested / deliberately outside scope

Native iOS and Android keyboard insets, hardware assistive technology, official organizer live services, current live Figma and physical smart-room devices. They cannot be marked PASS without corresponding evidence. Stage 5–7 not started.
