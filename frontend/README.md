# SAIN Smart Room — React/TypeScript client

Браузерный клиент команды 4Sain для кейса №2 хакатона SAIN × Школа 21. Это не официальный продукт SAIN.

## Установка и сборка

Node.js 24+, Python 3.11+. Команды в frontend:

~~~bash
npm ci
npm test
npm run build
~~~

Build выполняет TypeScript typecheck и генерирует dist; **dist и node_modules не коммитятся**.

## Локальная автономная демонстрация

Из корня проекта после установки Python requirements-dev.txt:

~~~bash
python -m scripts.rehearse_client
~~~

В отдельном терминале:

~~~bash
cd frontend
python serve.py --mode rehearsal
~~~

Из корня в третьем терминале: **python -m scripts.client_access dev --stay stay_test**. Откройте http://127.0.0.1:4173 и введите временный токен гостя. Для режима read-only: **python -m scripts.client_access final**. При перезагрузке страницы гостевой токен вводится снова — он не хранится в браузерном localStorage.

В режиме rehearsal используются FakeLLM и MockSimulator. Голосовой MediaRecorder записывает реальные данные микрофона, но ответ STT в этом режиме синтетический. Режим stand предназначен только для разрешённого доступа к историческому стенду организаторов.

## Проверка

~~~bash
npm test
npm run build
npx playwright install --with-deps chromium firefox
npm run e2e
SAIN_BROWSER=firefox npm run e2e
~~~

Playwright включает полные сценарии локального API, историю из 100 сообщений, 12 треков на 10 размерах, клавиатурный доступ и final read-only.

[Главный README](../README.md) · [Client API](../docs/client-api.md) · [Windows](../docs/WINDOWS_ACCEPTANCE_GUIDE_RU.md).
