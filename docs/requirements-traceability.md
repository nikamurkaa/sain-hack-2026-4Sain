# Матрица требований кейса 2

PASS относится к указанной проверке и данным. Оценивание организаторами проводится отдельно. Метрики и ограничения описаны в [результатах проверки](verification.md).

| Требование | Официальный источник | Файл реализации | Тест | Результат | Статус |
| --- | --- | --- | --- | --- | --- |
| brighter («Добавь света») | Кейс §3, §4, §9.1 | backend/intents.py, commands.py | tests/offline_cases.py → test_full_offline_http | Класс и все поля состояния совпали с эталоном. Намерение задаёт FakeLLM. | PASS |
| dimmer («Убавь свет») | Кейс §3, §4, §9.1 | backend/intents.py, commands.py | tests/offline_cases.py → test_full_offline_http | Класс и все поля состояния совпали с эталоном. Намерение задаёт FakeLLM. | PASS |
| warmer («Зябко») | Кейс §3, §4, §9.1 | backend/intents.py, commands.py | tests/offline_cases.py → test_full_offline_http | Класс и все поля состояния совпали с эталоном. Намерение задаёт FakeLLM. | PASS |
| cooler («Душно») | Кейс §3, §4, §9.1 | backend/intents.py, commands.py | tests/offline_cases.py → test_full_offline_http | Класс и все поля состояния совпали с эталоном. Намерение задаёт FakeLLM. | PASS |
| all_off («Выключи всё») | Кейс §3, §4, §9.1 | backend/intents.py, commands.py | tests/offline_cases.py → test_full_offline_http | Класс и все поля состояния совпали с эталоном. Намерение задаёт FakeLLM. | PASS |
| sound_on («Включи дождь») | Кейс §3, §4, §9.1 | backend/intents.py, commands.py | tests/offline_cases.py → test_full_offline_http | Класс и все поля состояния совпали с эталоном. Намерение задаёт FakeLLM. | PASS |
| quieter («Убавь звук») | Кейс §3, §4, §9.1 | backend/intents.py, commands.py | tests/offline_cases.py → test_full_offline_http | Класс и все поля состояния совпали с эталоном. Намерение задаёт FakeLLM. | PASS |
| curtains («Закрой шторы») | Кейс §3, §4, §9.1 | backend/intents.py, commands.py | tests/offline_cases.py → test_full_offline_http | Класс и все поля состояния совпали с эталоном. Намерение задаёт FakeLLM. | PASS |
| alarm_set («Разбуди в половине седьмого») | Кейс §3, §4, §9.1 | backend/intents.py, commands.py | tests/offline_cases.py → test_full_offline_http | Класс и все поля состояния совпали с эталоном. Намерение задаёт FakeLLM. | PASS |
| alarm_shift («Сдвинь на полчаса позже») | Кейс §3, §4, §9.1 | backend/intents.py, commands.py | tests/offline_cases.py → test_full_offline_http | Класс и все поля состояния совпали с эталоном. Намерение задаёт FakeLLM. | PASS |
| alarm_cancel («Отмени будильник») | Кейс §3, §4, §9.1 | backend/intents.py, commands.py | tests/offline_cases.py → test_full_offline_http | Класс и все поля состояния совпали с эталоном. Намерение задаёт FakeLLM. | PASS |
| going_to_bed («Я ложусь») | Кейс §3, §4, §9.1 | backend/intents.py, commands.py | tests/offline_cases.py → test_full_offline_http | Класс и все поля состояния совпали с эталоном. Намерение задаёт FakeLLM. | PASS |
| woke_up («Я проснулся») | Кейс §3, §4, §9.1 | backend/intents.py, commands.py | tests/offline_cases.py → test_full_offline_http | Класс и все поля состояния совпали с эталоном. Намерение задаёт FakeLLM. | PASS |
| like_yesterday («Как вчера») | Кейс §3, §4, §9.1 | backend/intents.py, commands.py | tests/offline_cases.py → test_full_offline_http | Класс и все поля состояния совпали с эталоном. Намерение задаёт FakeLLM. | PASS |
| do_not_disturb («Не беспокоить») | Кейс §3, §4, §9.1 | backend/intents.py, commands.py | tests/offline_cases.py → test_full_offline_http | Класс и все поля состояния совпали с эталоном. Намерение задаёт FakeLLM. | PASS |
| like_home («Как дома») | Кейс §3, §4, §9.1 | backend/intents.py, commands.py | tests/offline_cases.py → test_full_offline_http | Класс и все поля состояния совпали с эталоном. Намерение задаёт FakeLLM. | PASS |
| out_of_scope («Закажи такси») | Кейс §3, §4, §9.1 | backend/intents.py, commands.py | tests/offline_cases.py → test_full_offline_http | Класс и все поля состояния совпали с эталоном. Намерение задаёт FakeLLM. | PASS |
| warmer («Поставь 35 градусов») | Кейс §3, §4, §9.1 | backend/intents.py, commands.py | tests/offline_cases.py → test_full_offline_http | Класс и все поля состояния совпали с эталоном. Намерение задаёт FakeLLM. | PASS |
| medical («Что выпить для сна?») | Кейс §3, §4, §9.1 | backend/intents.py, commands.py | tests/offline_cases.py → test_full_offline_http | Класс и все поля состояния совпали с эталоном. Намерение задаёт FakeLLM. | PASS |
| R1 Вечерний свет 10–30%, ≤2700 K | Кейс §9.1, каталог sleep_rules | backend/scheduler.py | test_full_offline_http, test_sleep_oracle_detects_wrong_field | 10/10 в локальном наборе | PASS |
| R2 Ночь без света, шторы ≤10% | Кейс §9.1, каталог sleep_rules | backend/scheduler.py | test_full_offline_http, test_sleep_oracle_detects_wrong_field | 10/10 в локальном наборе | PASS |
| R3 Температурные интервалы по профилю | Кейс §9.1, каталог sleep_rules | backend/scheduler.py | test_full_offline_http, test_sleep_oracle_detects_wrong_field | 10/10 в локальном наборе | PASS |
| R4 Любимые звуки и таймер либо тишина | Кейс §9.1, каталог sleep_rules | backend/scheduler.py | test_full_offline_http, test_sleep_oracle_detects_wrong_field | 10/10 в локальном наборе | PASS |
| R5 Время и режим будильника | Кейс §9.1, каталог sleep_rules | backend/scheduler.py | test_full_offline_http, test_sleep_oracle_detects_wrong_field | 10/10 в локальном наборе | PASS |
| R6 Рассвет за 15–30 мин | Кейс §9.1, каталог sleep_rules | backend/scheduler.py | test_full_offline_http, test_sleep_oracle_detects_wrong_field | 10/10 в локальном наборе | PASS |
| R7 Тишина до подъёма | Кейс §9.1, каталог sleep_rules | backend/scheduler.py | test_full_offline_http, test_sleep_oracle_detects_wrong_field | 10/10 в локальном наборе | PASS |
| R8 Поправка на перелёт при разнице ≥3 ч | Кейс §9.1, каталог sleep_rules | backend/scheduler.py | test_full_offline_http, test_timezone_rule | 10/10 в локальном наборе | PASS |
| Д1. Материалы в срок | Инструкция, с. 9 | README.md | Внешняя сдача | Нужна форма команды | NOT_TESTED |
| Д2. Сданный SHA в репозитории | Инструкция, с. 9 | git | Внешняя сдача | Сдаваемый SHA выбирает команда | NOT_TESTED |
| Д3. Развёртывание по README | Инструкция, с. 9 | start.sh, workflows/deploy.yml | bash -n start.sh | Эта ветка на стенде не развёрнута | PARTIAL |
| Д4. HTTP 200 с финальным JSON в срок | Инструкция, с. 9 | main.py, backend/runner.py | test_full_offline_http, test_run_deadline_without_waiting | Локальный успех и таймаут 504. Реальные задержки неизвестны. | PARTIAL |
| Д5. Разрешённый прокси модели и STT | Инструкция, с. 9, кейс §5 | backend/clients.py | test_speech_uses_official_proxy_and_validates_text | Проверен маршрут с mock, действующая конфигурация закрыта | PARTIAL |
| Схемы входа и ответа | Официальные Case2Dataset и Case2Answers | backend/schemas | Сравнение JSON и проверка обоих объектов | Правила идентичны, в копиях опущены title и $schema, применяется Draft202012 | PASS |
| Назначенный токен и комплектность | Кейс §4, §8 | main.py, clients.py, runner.py | test_full_offline_http | Одна загрузка, 70 изолированных комнат, проверены все ссылки | PASS |
| История, профиль и источники | Кейс §3 | backend/core.py, preferences.py | test_history_is_scoped_and_bounded, test_invented_quote_rejected | Фильтры и валидация подтверждены. Семантика реальной модели зависит от истории. | PARTIAL |
| Без медицинских рекомендаций, только партнёрский отель сна | Кейс §5 | backend/commands.py | test_refusals_do_not_mutate, test_full_offline_http | Текстовые шаблоны и отказ локально, внешний medcheck не выполнялся | PARTIAL |
| 512 МиБ, 1 CPU, JSON ≤64 МБ | Инструкция, с. 8–9 | main.py, start.sh | Ограничение RLIMIT_AS, taskset и check_offline | Локальный набор в пределах бюджета. Закрытые данные и пик при одновременном аудио неизвестны. | PARTIAL |
| Один репозиторий, Python 3.11, без GPU | Кейс §5 | requirements.txt, start.sh, workflows/test.yml | Проверка грамматики 3.11, CI | Бэкенд одного процесса. Фронтенд впереди. | PARTIAL |
| Привязка dev-сеанса к прогону, 409, истечение | Официальный OpenAPI, уточнение команды | main.py, backend/clients.py | test_dev_run_owns_its_room_and_handles_closure, test_expired_session_does_not_read_upstream | Оценочные сеансы доступны для чтения, новые dev-команды изолированы | PASS |
| Клиент, заселение, сценарий, чат, виртуальное время | Кейс §1, §10 | main.py, docs/client-api.md | test_client_isolation_and_idempotency, test_openapi_contains_client_response_contract | Есть API и JSON-примеры. UI и приёмка в браузере впереди. | PARTIAL |
| Один финальный пользователь, управление на защите | Кейс §10 | main.py | test_final_session_allows_reads_and_rejects_mutations | Подготовка доступна спустя несколько часов. Живое чтение зависит от upstream. Запись для того же гостя после сохранения закрыта. [Матрица финала](final-defense.md). | PARTIAL |
| Голос по желанию | Кейс §6 | main.py, clients.py | tests/test_speech.py | API проверен на mock. Клиент и живой микрофон в этой ветке не проверялись. | PARTIAL |
| Подготовка сценария ≤10 секунд | Кейс §6 | backend/runner.py | check_offline | Локальный прогон с FakeLLM. Нет измерения с реальной сетью. | NOT_TESTED |
| Экран продолжения дома, новые привычки | Кейс §6, Q&A | Будущий интерфейс | — | Отложено до клиентского этапа | NOT_TESTED |
| Презентация ≤12 слайдов, очная защита | Кейс §10 | Будущий PDF | — | Этап финала | NOT_APPLICABLE |
