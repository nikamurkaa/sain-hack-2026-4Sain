import { test, expect } from "@playwright/test";

// Local loopback FastAPI + MockSimulator, not a visual-only intercepted fixture.
// A prepared plan explains choices; actual device state must come from GET state.
const api = "http://127.0.0.1:8765/api/v1";

test("Stage 2: six-device planned explanations have verifiable provenance on mobile and desktop", async ({ page, request }) => {
  const opened = await request.post(api + "/sessions", {
    headers: { Authorization: "Bearer offline-team" },
    data: { source: "dev", stay_id: "stay_test" },
  });
  expect(opened.status()).toBe(201);
  const auth = { Authorization: "Bearer " + (await opened.json()).session_token };
  const prepared = await request.get(api + "/prepared", { headers: auth });
  expect(prepared.status()).toBe(200);
  const data = await prepared.json();
  expect(new Set(data.explanations.map((item: { device_id: string }) => item.device_id))).toEqual(
    new Set(["light", "climate", "curtains", "sound", "alarm", "dnd"]),
  );
  expect(data.explanations.every((item: { status: string }) =>
    item.status === "planned" || item.status === "warning")).toBe(true);
  expect(JSON.stringify(data.explanations)).not.toMatch(/chat:|event:|profile:dislikes|secret|token/i);
  expect(data.last_confirmed).toBeNull(); // No live state was read yet.

  await page.goto("/");
  await page.getByLabel("Временный токен гостя").fill(auth.Authorization.slice("Bearer ".length));
  await page.getByRole("button", { name: "Подключиться", exact: true }).click();
  await expect(page.getByText("Заселиться", { exact: true })).toBeVisible();
  await page.getByText("Заселиться", { exact: true }).click();
  const summary = page.getByText("Почему выбран этот сценарий", { exact: true });
  await expect(summary).toBeVisible();
  await summary.click();
  await expect(page.getByText(/R3: на ночь выбрано/)).toBeVisible();

  await page.setViewportSize({ width: 1440, height: 900 });
  const desktopSummary = page.getByText("Почему выбран этот сценарий", { exact: true });
  await expect(desktopSummary).toBeVisible();
  await desktopSummary.click();
  await expect(page.getByText(/R3: на ночь выбрано/)).toBeVisible();
  const confirmed = await request.get(api + "/state", { headers: auth });
  expect(confirmed.status()).toBe(200);
  expect(Object.keys((await confirmed.json()).state).sort()).toEqual(
    ["alarm", "climate", "curtains", "dnd", "light", "sound"],
  );
});
