import { test } from "node:test";
import assert from "node:assert/strict";
import { ActionApiError, parseActionFailure } from "../src/api.ts";

test("MR-001: preserve verified structured partial evidence and a distinct type", () => {
  const received = parseActionFailure(409, {
    code: "ACTION_PARTIAL", message: "Подтверждена часть команды",
    operation_id: "op-123456", confirmed_devices: ["light"],
  });
  assert.ok(received instanceof ActionApiError);
  assert.equal(received.kind, "partial");
  assert.equal(received.operationId, "op-123456");
  assert.deepEqual(received.confirmedDevices, ["light"]);
  assert.equal(received.status, 409);
});

test("MR-001: classify conflicts/uncertain independently of all other HTTP 409", () => {
  assert.equal(parseActionFailure(409, {
    code:"ACTION_UNCERTAIN", operation_id:"op123", confirmed_devices: [],
  }).kind, "uncertain");
  assert.equal(parseActionFailure(409, {
    code:"ACTION_CONFLICT", operation_id:"op123", confirmed_devices: [],
  }).kind, "conflict");
  assert.equal(parseActionFailure(409, { code:"SESSION_READ_ONLY" }).kind, undefined);
});

test("MR-001: reject untrusted partial evidence instead of displaying unverified devices", () => {
  for (const body of [
    {code:"ACTION_PARTIAL", operation_id:"Bearer-secret", confirmed_devices:["light"]},
    {code:"ACTION_PARTIAL", operation_id:"ok", confirmed_devices:["admin"]},
    {code:"ACTION_PARTIAL", operation_id:"ok", confirmed_devices:["light","light"]},
    {code:"ACTION_PARTIAL", operation_id:"ok", confirmed_devices:"light"},
    {code:"ACTION_PARTIAL", operation_id:"ok", confirmed_devices:[]},
    null,
  ]) {
    const error = parseActionFailure(409, body);
    assert.ok(!(error instanceof ActionApiError), JSON.stringify(body));
  }
});
