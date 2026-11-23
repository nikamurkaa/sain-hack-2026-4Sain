# SAIN Smart Room — macOS demo

**Independent synthetic portfolio prototype, not an official SAIN product.** Offline mode uses no hosted model, official API or physical hotel device.

## Requirements and launch

1. Python 3.11+ is required, plus Internet for the first installation of pinned Python dependencies. The ZIP includes a prebuilt frontend; Node is not required for normal launching.
2. Extract the ZIP to a writable folder. Open Terminal in that directory and run: bash CHECK_ENV.command; bash START.command.
3. Open http://127.0.0.1:4173. Generate an ephemeral local GUEST token: .venv/bin/python -m scripts.client_access dev --stay stay_test. Paste the token into the browser, not an AI key.
4. To stop: bash STOP.command. Restarting with bash START.command restores unexpired OFFLINE guest sessions using the same guest token (enter it again after browser reload). Ports 4173 and 8765 must be free.
5. The .command scripts are unsigned and not notarized. A Finder launch may require manual permission or a Terminal launch.

## Authorized LIVE mode

Configure LLM_API_KEY, LLM_BASE_URL and LLM_MODEL in your own terminal, then run: SAIN_MODE=live bash START.command. Never paste these credentials into the browser. LIVE uses a synthetic local room and sends model requests only if explicitly configured. Expired tournament tokens must not be reused. No genuine provider acceptance is claimed by CI.

## Data and verification boundary

OFFLINE demo uses a local SQLite WAL database at .sain-state/demo.sqlite3 (override SAIN_DEMO_STATE_DB before launching). It stores hashed guest tokens, synthetic session/device journal and bounded dialogue history. Unexpired sessions recover after process restart; an uncertain action is blocked pending read-only reconciliation and is NEVER replayed. Stop with STOP.command before deliberately removing .sain-state to reset all synthetic state. Expired sessions are pruned and the simulator drops orphan logs on startup. LIVE mode does not persist sessions. No official tokens, audio or AI keys are stored. Local process and its files must remain private and writable; do not sync the database to a shared folder. Logs and PID files are under ignored .runtime.

Native CI exercises its macOS runner OS/architecture only. Apple Silicon, Intel desktops, physical mobile keyboards, assistive technology, live microphones, external SAIN APIs and hotel hardware are NOT TESTED unless separately evidenced.
