import { expect, test } from "@playwright/test";
import { mkdirSync } from "node:fs";

const host = "http://127.0.0.1:8765";
async function connect(page: import("@playwright/test").Page,
                       request: import("@playwright/test").APIRequestContext) {
  const started = await request.post(host + "/api/v1/sessions", {
    headers: { Authorization: "Bearer offline-team" },
    data: { source: "dev", stay_id: "stay_test" },
  });
  expect(started.status()).toBe(201);
  const token = (await started.json()).session_token as string;
  await page.goto("/");
  await page.getByLabel("Временный токен гостя").fill(token);
  await page.getByRole("button", { name: "Подключиться", exact: true }).click();
  await expect(page.getByRole("button", { name: "Заселиться" })).toBeVisible();
  await page.getByRole("button", { name: "Меню" }).click();
  await page.getByRole("navigation").getByRole("button", { name: "Диалог", exact: true }).click();
  return token;
}
async function say(page: import("@playwright/test").Page, text: string) {
  await page.getByRole("textbox", { name: "Просьба", exact: true }).fill(text);
  const response = page.waitForResponse((r) =>
    r.url().endsWith("/api/v1/messages") && r.request().method() === "POST");
  await page.getByRole("button", { name: "Отправить просьбу" }).click();
  return await response;
}
async function close(request: import("@playwright/test").APIRequestContext, token: string) {
  await request.delete(host + "/api/v1/session", {
    headers: { Authorization: "Bearer " + token },
  });
}

for (const size of [
  { width: 375, height: 812, name: "mobile" },
  { width: 1440, height: 900, name: "desktop" },
]) {
  test("MR-001: REAL REHEARSAL partial flow and safe refresh " + size.name,
    async ({ page, request, browserName }) => {
    await page.setViewportSize({ width: size.width, height: size.height });
    const token = await connect(page, request);
    try {
      let posts = 0;
      page.on("request", r => { if (r.url().endsWith("/api/v1/messages") && r.method() === "POST") posts++; });
      const response = await say(page, "Проверка частичного выполнения");
      expect(response.status()).toBe(409);
      const received = await response.json();
      expect(received.code).toBe("ACTION_PARTIAL");
      expect(received.confirmed_devices).toEqual(["light"]);
      expect(typeof received.operation_id).toBe("string");
      const panel = page.locator('[data-action-kind="partial"]');
      await expect(panel).toBeVisible();
      await expect(panel).toContainText("Просьба выполнена частично");
      await expect(panel).toContainText("Свет");
      await expect(panel).toContainText("Остальные изменения не подтверждены");
      await expect(panel).not.toContainText("Готово");
      await expect(page.getByRole("button", { name: "Повторить", exact: true })).toHaveCount(0);
      await expect(panel.getByRole("status")).toContainText("Фактическое состояние получено");
      const state = await request.get(host + "/api/v1/state", {
        headers: { Authorization: "Bearer " + token },
      });
      expect(state.status()).toBe(200);
      expect((await state.json()).state.light.brightness).toBe(0);
      expect(posts).toBe(1);
      mkdirSync("evidence", { recursive: true });
      await page.screenshot({
        path: `evidence/mr001-partial-${browserName}-${size.name}.png`,
        fullPage: true,
      });
      // Keyboard-only recovery must never emit another mutation.
      const refresh = panel.getByRole("button", { name: "Обновить состояние номера" });
      await refresh.focus();
      await expect(refresh).toBeFocused();
      await page.keyboard.press("Enter");
      await expect(panel.getByRole("status")).toContainText("Фактическое состояние получено");
      expect(posts).toBe(1);
      // Browser reload demands re-authentication and MUST NOT replay actions.
      await page.reload();
      await expect(page.getByLabel("Временный токен гостя")).toBeVisible();
      expect(posts).toBe(1);
    } finally { await close(request, token); }
  });
}

test("MR-001: GET state unavailable keeps partial outcome explicitly stale", async ({ page, request }) => {
  const token = await connect(page, request);
  try {
    const response = await say(page, "Проверка частичного выполнения без состояния");
    expect(response.status()).toBe(409);
    const panel = page.locator('[data-action-kind="partial"]');
    await expect(panel).toBeVisible();
    await expect(panel.getByRole("status")).toContainText("Актуальное состояние не подтверждено");
    await expect(panel).toContainText("Свет");
    await expect(panel.getByRole("button", { name: "Закрыть уведомление" })).toBeDisabled();
    const send = page.getByRole("button", { name: "Отправить просьбу" });
    await expect(send).toBeDisabled();
    await panel.getByRole("button", { name: "Обновить состояние номера" }).click();
    await expect(panel.getByRole("status")).toContainText("Фактическое состояние получено");
  } finally { await close(request, token); }
});

for (const [phrase, kind, text] of [
  ["Проверка конфликта состояния", "conflict", "Обнаружено расхождение"],
  ["Проверка неопределённого результата", "uncertain", "Результат просьбы пока неизвестен"],
] as const) {
  test("MR-001: typed " + kind + " never appears as done or final read-only", async ({ page, request }) => {
    const token = await connect(page, request);
    try {
      const response = await say(page, phrase);
      expect(response.status()).toBe(409);
      const panel = page.locator('[data-action-kind="' + kind + '"]');
      await expect(panel).toBeVisible();
      await expect(panel).toContainText(text);
      await expect(panel).not.toContainText("Готово");
      await expect(page.getByRole("button", { name: "Повторить", exact: true })).toHaveCount(0);
    } finally { await close(request, token); }
  });
}
