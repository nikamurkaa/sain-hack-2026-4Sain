# sain-smart-room

«Сэйн × Школа 21», команда team25. Кейс №2 «Номер, который знает гостя».

## Текущий статус

Подготовлен минимальный стартовый сервер по официальному `sample-app` организаторов.
Решение кейса, интерфейс, персонализация и ИИ-логика **не реализованы**.
Успешный деплой стартового сервера подтверждает только работу инфраструктуры.

- `GET /` и `GET /health`: HTTP 200, `{"team":"team25","status":"ok"}` на стенде.
- `POST /run` с корректным JSON без Bearer: HTTP 401.
- `POST /run` с корректным JSON и Bearer: HTTP 501,
  `{"status":"not_implemented","case":2}`. Проверяется наличие схемы Bearer,
  а не действительность токена; бизнес-логика отсутствует.
- Контракт тела: `{"case":2,"dataset_code":"case2-dev-v1"}`.
  Некорректное тело запроса возвращает 422 согласно FastAPI/Pydantic.

## Локальный запуск

Используйте Python 3.11 и Bash (Windows: WSL или Git Bash).

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
TEAM=team25 PORT=8000 bash start.sh
```

Сервер слушает `0.0.0.0` и порт из `PORT` (по умолчанию 8000).
Зависимости сохранены из официального примера: FastAPI 0.162.6, Uvicorn 0.54.0.
Для стартового сервера API/LLM-ключи не требуются.

```bash
curl --fail http://127.0.0.1:8000/health
curl -i -X POST http://127.0.0.1:8000/run \
  -H 'Content-Type: application/json' \
  -d '{"case":2,"dataset_code":"case2-dev-v1"}'
curl -i -X POST http://127.0.0.1:8000/run \
  -H 'Content-Type: application/json' -H 'Authorization: Bearer smoke-test' \
  -d '{"case":2,"dataset_code":"case2-dev-v1"}'
```

## Автоматический деплой

`.github/workflows/deploy.yml` на основе официального workflow запускается при push в `main`
или вручную через Actions → «Деплой на стенд хакатона» → Run workflow.
Единственный обязательный repository secret — `STAND_SSH_KEY`:
весь приватный SSH-ключ из набора организаторов. Никогда не коммитьте его.
Адрес SSH и доверенные ключи хоста уже записаны в workflow;
отдельные `STAND_HOST` и `STAND_KNOWN_HOSTS` не нужны.
Проверка SSH host key включена, текущая сборка не отменяется новым push.

Workflow передаёт `git archive HEAD` и `$GITHUB_SHA` стенду.
Подтверждение конкретного деплоя: зелёный запуск Actions, строка
`OK: sha=<SHA коммита>` в логе, совпадение SHA и проверка HTTP.
Один ответ `/health` не доказывает, что развёрнут новый коммит.

К официальным шагам добавлена автоматическая проверка после деплоя:
SSH `status` должен содержать текущий `GITHUB_SHA`, `/` и `/health` должны
вернуть ожидаемый JSON с HTTP 200, `/run` — 401 без Bearer и 501 с тестовым
Bearer. Проверка использует стандартную библиотеку Python и не передаёт
настоящие токены приложения. SSH host key проверяется строго.
Когда будет реализовано решение кейса, замените проверку 501 тестом нового
контракта `/run`; текущая проверка намеренно подтверждает только заготовку.

Стенд: https://team25.hack.be-healthy.tech
Health: https://team25.hack.be-healthy.tech/health

Из **внешней папки набора организаторов**, не из репозитория:

```bash
chmod 600 id_ed25519
ssh -i id_ed25519 -o UserKnownHostsFile=known_hosts \
  -o StrictHostKeyChecking=yes -o IdentitiesOnly=yes \
  deploy@hack.be-healthy.tech status
```

## Ограничения стенда

- Python 3.11 (`python:3.11-slim`), 512 МБ RAM, 1 CPU, до 256 процессов.
- Зависимости устанавливаются из корневого `requirements.txt` при сборке.
- Запуск без root, uid 10001; `/tmp` до 256 МБ. Локальные файлы исчезают при деплое.
- Интернет приложения закрыт, доступны только API хакатона и прокси LLM.
- `TEAM`, `PORT`, `HACK_API_URL`, `HACK_TEAM_TOKEN`, `LLM_BASE_URL`,
  `LLM_API_KEY`, `LLM_MODEL` предоставляет стенд; не дублируйте секреты.
- HTTP-ответ на `/` нужен за 60 секунд, иначе стенд откатывает версию.
- Архив до 50 МБ, распакованный код до 300 МБ; без данных, моделей и venv.
- Деплой не чаще раза в минуту, общая очередь до 40 минут, сборка до 15 минут.
- Dockerfile и .dockerignore игнорируются. Отдельные VPS, DNS, Nginx,
  HTTPS и Docker Compose этому проекту не нужны.
- 20.11.2026 в 12:00 МСК деплой закрывается для онлайн-проверки.

Не храните и не логируйте ключи, токены, заголовки авторизации и коды закрытых наборов.
Участников команды добавляет владелец отдельно.
