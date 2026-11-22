# SAIN Stage 3 — Official Dev Real-Token Acceptance

**Date:** 2026-11-22 (MSK). **Source main SHA:** `4941f0be9a6531b553aeb50cccc75d4fd2c433e8`.
**Status:** **NOT TESTED / blocked by networking**. This is not an HTTP 401 and does not establish that either credential expired.

| Проверка | Результат | Доказательство |
|---|---|---|
| Official API /health | NOT TESTED | HTTPSConnectionPool: DNS NameResolutionError in sandbox; no HTTP response |
| Token authorization | NOT TESTED | Key exists in private uploaded ZIP; never sent over successful transport |
| Official dev getData | NOT TESTED | Public service unreachable; no dataset downloaded |
| Official schemas | NOT TESTED on dev | GitHub contains Case2Dataset/Case2Answers schemas; no real dataset to validate |
| Official stays | 0/? NOT TESTED | Official number of records unknown |
| Official requests | 0/? NOT TESTED | Official number of records unknown |
| Official dev reference | NOT TESTED | Reference unavailable |
| Local dev /run | NOT TESTED on official API | Real upstream cannot be accessed |
| Official /validate | NOT TESTED | No request sent; no 501 falsely counted as PASS |
| Official dev simulator | NOT TESTED | No authorized live simulator session created |
| Official team25 /health | NOT TESTED | DNS NameResolutionError in sandbox |
| Official OpenAPI | NOT TESTED | Direct sandbox DNS failed; web fetch returned 502 |
| Bifrost /models | NOT TESTED | No authorized network response |

## Evidence and scope
- The attached `team25.zip` has `team25/README.md`, `api.token`, `llm.key`, deployment materials and a SSH key. Raw secret content was **never printed, logged, committed or passed to GitHub**.
- Sandbox direct GET to `https://hack-api.be-healthy.tech/health` failed at DNS resolution before any HTTP status could be obtained. Same for `/openapi.json` and `https://team25.hack.be-healthy.tech/health`.
- Separate public web retrieval did not return verifiable API responses; not a valid service health measurement.
- **No real authorized dataset fetch, no POST to official services, no official simulator mutation, no rerun of online/final assessment.**
- Per official README, team API token expires **2026-11-23 00:00 MSK** and AI token **2026-11-23 12:00 MSK**. Presence in a ZIP is not proof of validity.
- The repository's `scripts/check_dev.py` is a pre-existing official dev harness. It uses `GET /case/2/getData`, `POST /runs`, real `Solution.run()`, reference comparison and `POST /case/2/validate`, but **was not executable against the official service in this environment**.
- README warns official case 2 `validate` may return HTTP 501. Must be recorded as LIMITATION, not PASS.
- No numerical C/S/x reported because no official reference was available.

## Next gate
Run from an **authorized, network-capable machine** with credentials loaded only into environment variables; use official OpenAPI for current schema. Obtain dataset once, verify `/runs` and simulator endpoints, then execute bounded dev harness and separately validate. Do not publish dataset/reference/session tokens or retry uncertain POSTs.
