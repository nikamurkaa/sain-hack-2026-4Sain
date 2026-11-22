# SAIN Stage 1 — Architecture Decisions

Date: 2026-11-22. Baseline: 2820222613c4ea4544b715435aeba59988470783.
Status: **ADR-001 accepted in prototype scope; ADR-002 durable storage deferred (BLOCKED on external integration semantics).**
Scope: autonomous REHEARSAL and existing Case2 APIs. No official /run and no post-final read-only bypass.

## ADR-001: non-atomic command operations

**Decision:** use an ordered, fail-closed *saga* at the room adapter boundary rather than claim a transactional upstream batch. Proposed in Draft PR #17. The upstream API provides individual POST /action operations and GET /state; there is no documented atomic batch or compensation protocol.

1. Plan all device actions first; validate allowed device fields and numerical bounds before issuing any POST.
2. Allocate an opaque operation ID for each invocation and a stable fingerprint of timestamp + ordered commands. The existing guest API additionally uses a client-supplied Idempotency-Key, scoped to its ClientSession, with a body fingerprint.
3. Start from a confirmed snapshot at the requested instant; execute commands in sequence; after each action reconcile the **whole** state, not merely the updated property.
4. Log only confirmed steps (device identifiers), completed snapshots and status. Distinguish done, partial, failed, uncertain and conflict. GET failure after a possibly successful POST is **uncertain**, not safe to retry.
5. For a second invocation of the same operation ID, return a cached fully confirmed result, otherwise fail closed; never issue a second POST if the previous outcome is uncertain.
6. For partial completion, report which devices were confirmed; stop subsequent commands and never send “Готово”. Do not attempt blind rollback.
7. Reconciliation compares snapshots at the same timestamp to avoid treating scheduled actions as manual command effects. Concurrent external changes cause an explicit conflict; no overwrite or assumption of ownership.

**Limitations:** an in-memory Room.operations journal does not survive restarts. Session-level cache provides a separate additional guard, but both disappear with the Python process. The simulator may perform other side effects that cannot be inferred solely from a GET snapshot; without a documented event ID or authoritative operation log, that case stays uncertain. Operation ID is currently per Room execution (not yet a durable distributed job identity). This ADR makes no exactly-once promise across a process crash.

**Rollback:** revert PR #17; note this removes partial-step diagnostics and must not be treated as removing underlying upstream non-atomicity.

## ADR-002: minimum durable entities and explicit lifecycle

**Decision:** retain the modular monolith, no Kubernetes/queue or PostgreSQL at this stage. Introduce no “durable sessions” claim until the official external session-reconciliation contract and data-retention authority are established. Use SQLite with WAL and versioned migrations if a post-hackathon independent local simulator is authorized; start with the smallest table set necessary.

Minimum conceptual schema:
| Entity | Stable ID / relationships | Required data | Persist in future? |
|---|---|---|---|
| Guest | guest_id | Synthetic/consented ID; never infer a name from opaque ID | Only with retention authorization |
| Stay | stay_id + guest_id | Hotel IANA zone, start, wake, expiry, mock/upstream provenance | Yes for local demo; avoid source tokens |
| RoomSession | session_id + stay_id | Source, status, local simulator cursor, expiry, access-control class | Local/demo only; **never assume upstream reconnect** |
| Command | operation_id + session_id, unique idempotency scope | Input fingerprint, creation time, status, response classification | Yes, as a minimum journal |
| CommandStep | operation_id + sequence | Device, target fields (non-sensitive), confirmation, error kind | Yes, minimal |
| RoomSnapshot | session_id + observed_at | Confirmed actual state, provenance, recency; immutable | Optionally, bounded |
| Event | event_id + operation_id | Attempt/confirmed/uncertain markers and coarse timing | Optionally, bounded |
| Scenario | stay_id | Planned events, plan version | Yes, strictly separate from actual |
| ConversationEntry | session_id | Redacted textual conversation | **Deferred** until retention/privacy decision |
| PreferenceFact | guest_id + evidence reference | Consent, provenance, expiry | **Deferred** until retention/privacy decision |

Concrete SQLite design for a future approved local-only adapter: SQLite WAL, foreign keys ON, transactional upsert for (session_id,idempotency_key), unique (operation_id,step_index), SQLite write transaction before upstream mutation, atomic status transition to confirmed after verifying external state. A crash between POST and confirmation must resume **reconciliation, not re-POST**. An unknown result cannot be promoted to done. Migrations must be reversible with explicit schema_version; no persistent storing of raw guest tokens, service keys, personal audio, bearer headers, or upstream request bodies. Hashing a bearer token may still be sensitive; derive short-lived session identities under a keyed server-side mechanism when needed, and store credentials only in approved secret storage.

### Restart: actual vs planned

- **Actual state:** only a snapshot confirmed by simulator GET /state at a specified instant. Mark it stale after restart; never silently present it as current.
- **Planned state:** R1–R8 steps from build_scenario, never evidence of executed actions.
- **After restart:** current implementation intentionally invalidates guest tokens, ephemeral idempotency, in-flight operations, /run cache and final-session presentation. REHEARSAL creates a **new** isolated local simulated room. A real upstream RoomSession cannot automatically reattach without documented API capability, so failure must remain visible.
- **Should survive only after future permission:** non-sensitive operation status, time/correlation, verified device snapshots and minimal error reason, and a local stay identity, with bounded retention.
- **Must never be written by default:** official tokens, raw recordings, prompt/model secret payloads, private ZIP contents, bearer credentials, full incoming HTTP headers.
- **Isolation:** key any future records by tenant + guest + stay + simulator namespace; authorization must verify session ownership on every request; never authorize solely from a guest display name.
- **Deletion:** defined retention period + DELETE for synthetic/consented guest data, cascading related rows, ephemeral cache invalidation and expiration; verify backup deletion separately.
- **Compatibility:** do not mutate the existing /run answer schema, read-only final access, or current offline rehearsal API shape in Stage 1.

### Why deferred

The upstream /room/session POST currently returns a session ID only after successful response. There is **no confirmed documented lookup or reattachment** endpoint for a lost response or post-restart recovery; preserving the old local token would risk falsely authorizing an inaccessible upstream session. Persistence also needs a finalized authorization/retention policy for user history and partner material. Adding SQLite now cannot solve either of these external dependencies and could create a false exactly-once guarantee.

**Decision gate:** build a separately reviewable Stage 6 storage PR once either (a) a fully local simulator is the only authority, or (b) upstream operation/session reconciliation and permitted retention are documented. Until then classify S-002/S-024 as PARTIAL and label the restart boundary explicitly.

## ADR-003: time and identity

Hotel timezone is the IANA identifier attached to each Stay (Europe/Moscow, Europe/Berlin, America/New_York). Serialize real moments as ISO 8601 with an explicit date-appropriate offset; validate that wall clock and offset belong to the hotel IANA zone. At DST fall-back, an explicit offset selects the occurrence; spring-forward nonexistent wall clocks are rejected. Frontend preview points are GET-only and do not mutate confirmed room state.

The official Case2 user schema does not provide display_name and rejects undeclared properties. Use neutral guest labels; never infer an identity from user_id, fake source material or Figma placeholder “Алина”.

## Traceability

- PR #14: R6 scheduler under short stays.
- PR #15: IANA/DST time previews and backend validation.
- PR #17: non-atomic action journal and status.
- PR #16: no automatic retry of creating POST /room/session.
- PR #18: neutral verified guest display.
- Original official Case2 §9 R1–R8 and audit problem register S-002, S-003, S-004, S-008, S-009, S-010, S-024.

All PRs remain Draft; architecture is a set of reviewable decisions, **not** evidence that a persistent database or external integration has been delivered.
