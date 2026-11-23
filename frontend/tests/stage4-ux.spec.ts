import { expect, test } from "@playwright/test";

const api = "http://127.0.0.1:8765/api/v1";
// Reuse one synthetic dev session across these independent UI assertions.
// The simulator rate-limits session creation; a new session per test would
// exhaust the shared budget already used by the other regression suites.
test.describe.configure({ mode: "serial" });
let sharedToken = "";
test.beforeAll(async ({ playwright }) => {
  const http = await playwright.request.newContext();
  try {
    const created = await http.post(api + "/sessions", {
      headers: { Authorization: "Bearer offline-team" },
      data: { source: "dev", stay_id: "stay_test" },
    });
    expect(created.status()).toBe(201);
    sharedToken = (await created.json()).session_token as string;
  } finally {
    await http.dispose();
  }
});
async function connect(page: import("@playwright/test").Page) {
  await page.goto("/");
  await page.getByLabel("Временный токен гостя").fill(sharedToken);
  await page.getByRole("button", { name: "Подключиться", exact: true }).click();
  await expect(page.getByRole("button", { name: "Заселиться" })).toBeVisible();
}
async function navigate(page: import("@playwright/test").Page, item: string) {
  await page.getByRole("button", { name: "Меню" }).click();
  await page.getByRole("navigation").getByRole("button", { name: item, exact: true }).click();
}

test("Stage 4: planning warnings are immediately perceivable on mobile and desktop", async ({ page }) => {
  await page.route("**/api/v1/prepared", async (route) => {
    const response = await route.fetch();
    const prepared = await response.json();
    prepared.explanations = (prepared.explanations ?? []).map(
      (item: { reason: string }) => item.reason.startsWith("R6:")
        ? { ...item, status: "warning", reason: "R6: интервал рассвета 15–30 минут перед подъёмом недоступен. Полное выполнение правила не подтверждено." }
        : item,
    );
    await route.fulfill({ response, json: prepared });
  });
  await connect(page);
  await page.getByRole("button", { name: "Заселиться" }).click();
  const warning = page.getByRole("alert", { name: "Предупреждения сценария" });
  await expect(warning).toBeVisible();
  await expect(warning).toContainText("R6: интервал рассвета 15–30 минут перед подъёмом недоступен");
  await page.setViewportSize({ width: 1440, height: 900 });
  await expect(warning).toBeVisible();
  await expect(warning).toContainText("R6:");
});

test("Stage 4: climate uses confirmed-action Save instead of static Applied artwork", async ({ page }) => {
  await connect(page);
  await navigate(page, "Мой номер");
  await page.getByRole("button", { name: "Климат", exact: true }).click();
  const save = page.getByRole("button", { name: "Сохранить" });
  await expect(save).toBeVisible();
  await expect(page.getByText(/Применям|Установлено 21 °C/)).toHaveCount(0);
  await page.getByRole("spinbutton", { name: "Температура" }).fill("35");
  await expect(save).toBeDisabled();
  await page.getByRole("spinbutton", { name: "Температура" }).fill("21");
  await expect(save).toBeEnabled();
});

test("Stage 4 Phase 2: climate preview never claims server confirmation", async ({ page }) => {
  await connect(page);
  await navigate(page, "Мой номер");
  await page.getByRole("button", { name: "Климат", exact: true }).click();
  const preview = page.locator(".climate-edit-summary");
  await expect(preview).toBeVisible();
  await expect(preview).toContainText("Текущая настройка");
  await page.getByRole("spinbutton", { name: "Температура" }).fill("21");
  await expect(preview).toContainText("Изменение климата");
  await expect(preview).toContainText("только после подтверждения");
  await expect(page.getByText(/Применено|Успешно сохранено/)).toHaveCount(0);
});

test("Stage 4 Phase 2: alarm draft has accessible signal and a real time control", async ({ page }) => {
  await connect(page);
  await navigate(page, "Мой номер");
  await page.getByRole("button", { name: "Будильник", exact: true }).click();
  const input = page.getByLabel("Время пробуждения");
  await expect(input).toBeVisible();
  await input.fill("07:45");
  await expect(page.getByRole("status")).toContainText("07:45");
  await expect(page.getByLabel("Сигнал")).toBeVisible();
  await expect(page.getByRole("button", { name: "Сохранить" })).toBeEnabled();
  await expect(page.locator(".unavailable-option")).toContainText("Повтор недоступен");
});

test("Stage 4: core mobile controls remain scroll-reachable at 320x568", async ({ page }) => {
  await page.setViewportSize({ width: 320, height: 568 });
  await connect(page);
  await navigate(page, "Диалог");
  const dock = page.locator(".compact-chat-dock");
  await expect(dock).toBeVisible();
  const composer = page.getByRole("textbox", { name: "Просьба" });
  await expect(composer).toBeVisible();
  // Test without scrolling: the short-screen fix is a fixed, reachable composer.
  await expect(composer).toBeInViewport();
  await expect(page.getByRole("button", { name: "Отправить просьбу" })).toBeInViewport();
  const width = await page.evaluate(() => document.documentElement.scrollWidth);
  expect(width).toBeLessThanOrEqual(321);
});

test("Stage 4: uncertain transport error has no illustrative pseudo-Retry button", async ({ page }) => {
  await page.route("**/api/v1/messages", (route) => route.abort("failed"));
  await connect(page);
  await navigate(page, "Диалог");
  await page.getByRole("textbox", { name: "Просьба" }).fill("Сделай попрохладнее");
  await page.getByRole("button", { name: "Отправить просьбу" }).click();
  const error = page.locator(".delivery-error");
  await expect(error).toBeVisible();
  await expect(error).toContainText("Перед повторной командой проверьте состояние номера.");
  await expect(error.getByRole("button", { name: "Повторить" })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Отправить просьбу" })).toBeDisabled();
});

