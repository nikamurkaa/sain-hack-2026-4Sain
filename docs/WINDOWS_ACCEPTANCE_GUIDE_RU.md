# SAIN Smart Room — Windows: локальная репетиция

Это портфолио-прототип команды 4Sain, **не** официальный продукт SAIN.

1. В GitHub Actions запустите **Build portable Windows demo** и скачайте артефакт **sain-windows-demo**. Распакуйте вложенный Windows ZIP полностью.
2. Требуется Windows 10/11 и Python 3.11+. Node.js не требуется, потому что готовый ZIP содержит frontend/dist. Запустите CHECK_ENV.cmd.
3. Откройте START.cmd и выберите **1 = REHEARSAL** (без официального API). При первом запуске может понадобиться интернет для Python-зависимостей.
4. Откройте http://127.0.0.1:4173, а в CMD из папки архива выполните **.venv\Scripts\python.exe -m scripts.client_access dev --stay stay_test**. Скопируйте выданный гостевой токен в интерфейс.
5. Пройдите заселение, персональный план, настройки шести устройств, запрос «Сделай попрохладнее», диалог, профиль и виртуальное время. Для read-only выдайте новый токен командой **.venv\Scripts\python.exe -m scripts.client_access final**.
6. Для остановки используйте STOP.cmd. При ошибках запустите RESET_TEST_STATE.cmd и START.cmd, затем создайте новый локальный токен. Не завершайте чужие процессы при конфликте портов.
7. Проверка responsive: Chrome F12 → Ctrl+Shift+M → 375×812; desktop 1440×900 и 1920×1080, масштаб Ctrl+0.

**Никогда не вводите командный ключ, SSH-ключ и LLM API-key в браузер и не включайте токены в видео.** Режим STAND использует исторический стенд организаторов и требует официальных разрешений; для репетиции не нужен. Закрытый final read-only, HTTP 409 не обходится.

## Самостоятельная сборка ZIP

Из checkout Git сначала **cd frontend && npm ci && npm run build**, затем из корня **python scripts/build_windows_candidate.py**. Скрипт создаёт ZIP с SHA-256 и проверяет CRC. CI Linux не является нативным Windows acceptance.
