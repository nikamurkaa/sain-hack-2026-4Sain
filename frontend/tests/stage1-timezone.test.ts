import { test } from "node:test";
import assert from "node:assert/strict";
import { moments } from "../src/model.ts";

test("S-004: Berlin spring-forward morning uses hotel offset +02 not frozen +01", () => {
  const slots = moments("2026-03-29T01:30:00+01:00", "2026-03-29T07:00:00+02:00", [], "Europe/Berlin");
  assert.ok(slots.morning?.endsWith("+02:00"), slots.morning);
  assert.equal(slots.morning?.slice(11, 16), "06:00");
});
test("S-004: New York autumn repeated hour retains correct instant and offset", () => {
  const slots = moments("2026-11-01T00:30:00-04:00", "2026-11-01T08:00:00-05:00", [], "America/New_York");
  assert.ok(slots.morning?.endsWith("-05:00"), slots.morning);
  assert.equal(slots.morning?.slice(11, 16), "06:00");
});
