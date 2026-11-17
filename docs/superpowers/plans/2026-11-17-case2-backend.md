# Case 2 backend implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement the nine backend tasks approved in chat, verify against the organizer simulator, and provide a client contract.
**Architecture:** FastAPI entry point; separate data client, preference resolver, deterministic scheduler, LLM intent parser, command executor and run coordinator. Client sessions are isolated from evaluation sessions.
**Tech Stack:** Python 3.11, FastAPI, httpx, Pydantic, jsonschema, pytest; organizer LLM proxy.
**Spec:** User's nine-task request; attached organizer README and current https://hack-api.be-healthy.tech/openapi.json.

## Global constraints
512 MB RAM, 1 CPU; runtime network limited to organizer API and LLM proxy. Root start.sh and requirements.txt remain. Credentials never enter source, logs or client responses. Read LLM model from environment. 45-minute online budget. Datetimes include explicit UTC offsets; no Z. Evaluation input token is used for dataset and room access. Reference answers are test-only.

## Architecture decisions
- backend/clients.py: bounded HTTP timeouts/retries, no credential logging; mutation timeouts reconciled via state/log before retry.
- backend/preferences.py: user-scoped history bounded by record time; provenance and temporary versus persistent preferences.
- backend/scheduler.py: compile exact dataset R1–R8 into room scenario; device schemas authoritative.
- backend/intents.py: validated structured LLM output for 19 intents; deterministic validation and arithmetic.
- backend/room.py: session creation, scenario/action execution, state confirmation.
- backend/runner.py: load dataset once; separate stay/request sessions; ordered utterances; Case2Answers validation.
- backend/app_api.py: separate client session token, guest/scenario/state/message endpoints; no raw upstream secrets.
- main.py: health, evaluation route, app routes and dependency wiring.
- docs/client-api.md: versioned request/response examples for Alexey and Pavel.
- tests/: unit tests and mocked transport; opt-in live dev verification.

## Tasks
- [ ] 1. Capture current schemas and inspect dev data privately. Confirm final client-session lifecycle: current /runs description says final has persistent access and no batch submission, unlike README. Record the discrepancy; do not invent permissions.
- [ ] 2. Write tests for single dataset fetch, authorization forwarding, user/time isolation, reference exclusion, transient errors. Implement clients and preference resolver. Run pytest tests/test_data.py tests/test_preferences.py.
- [ ] 3. Write boundary tests for R1–R8, midnight, timezone shift of exactly one hour where applicable, late arrivals, sounds absent and explicit sound shutdown. Implement build_scenario(user, history, stay, catalog, rules). Run pytest tests/test_scheduler.py.
- [ ] 4. Write tests for 19 intents, two utterances, invalid temperature, unrelated fields preserved, malformed LLM JSON, future-history exclusion and medical/out-of-scope refusal. Implement parse_intent and validated command planning. Run pytest tests/test_intents.py tests/test_commands.py.
- [ ] 5. Write transport tests for initial state, session kinds, successful execution, partial/ambiguous failures and no false done. Implement simulator adapter. Run pytest tests/test_room.py.
- [ ] 6. Write integration tests for complete /run with incoming token, all records and output schema; health stays responsive during work. Implement coordinator with bounded concurrency and independent request states. Run pytest tests/test_run.py.
- [ ] 7. Write client-session isolation and idempotency tests. Implement create-session, guest, scenario, state and messages endpoints; derive exact upstream lifecycle from step 1. Publish OpenAPI/examples. Run pytest tests/test_app_api.py.
- [ ] 8. Replace deployment assertions requiring 501 and exact root JSON with stable health and cheap validation checks. Add Python 3.11 CI for unit tests; live LLM runs remain opt-in.
- [ ] 9. Run full unit suite and a real dev run; validate references/schema and independently compare states/sleep rules against dev reference. Report measured results, request/token usage and unresolved failures. Publish branch and reviewable PR; never claim validate proves semantic quality.

## Review focus
- Two guests and overlapping stays must not share state, tokens or history.
- Relative command retries must not apply twice.
- LLM failures must not fabricate successful mutations.
- Evaluation session freezing must not break live demo.
- Inconsistent/missing preference and time data need documented fallback or explicit failure.

## Delivery
Working feature branch, test evidence, API contract, limitations and deployment smoke-check update. Existing main stays runnable until replacement is verified.
