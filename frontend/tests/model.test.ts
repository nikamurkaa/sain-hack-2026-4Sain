import { test } from "node:test";
import assert from "node:assert/strict";
import { describe, moments, periodAt, preferenceItemLabel } from "../src/model.ts";
test("overnight stay offers only reachable periods with explicit offsets", () => {
  const start = "2026-11-12T20:30:00+03:00",
    end = "2026-11-13T07:00:00+03:00";
  const options = moments(start, end, []);
  assert.equal(options.day, undefined);
  assert.deepEqual(Object.keys(options).sort(), [
    "evening",
    "morning",
    "night",
  ]);
  for (const [p, at] of Object.entries(options)) {
    assert.equal(periodAt(at), p);
    assert.ok(
      Date.parse(at) >= Date.parse(start) && Date.parse(at) <= Date.parse(end),
    );
    assert.ok(at.endsWith("+03:00"));
  }
});
test("distinguishes unavailable readings and confirmed zero", () => {
  assert.equal(describe("light", {}), "—");
  assert.equal(describe("light", { brightness: 0 }), "0 %");
  assert.equal(describe("alarm", { at: null }), "Выключен");
  assert.equal(describe("dnd", { enabled: false }), "Выключен");
});

test("known technical preference IDs are localized for the guest profile", () => {
  assert.deepEqual(
    ["temperature", "tracks", "volume", "timer", "alarm_mode"].map(preferenceItemLabel),
    ["Температура", "Звуки", "Громкость", "Таймер звука", "Режим пробуждения"],
  );
  assert.equal(preferenceItemLabel("custom_setting"), "custom setting");
});
