import { expect, test } from "@playwright/test";

const api = "http://127.0.0.1:8765/api/v1";
async function connect(page: import("@playwright/test").Page, request: import("@playwright/test").APIRequestContext) {
  const created = await request.post(api + "/sessions", {
    headers: { Authorization: "Bearer offline-team" },
    data: { source: "dev", stay_id: "stay_test" },
  });
  expect(created.status()).toBe(201);
  const token = (await created.json()).session_token as string;
  await page.goto("/");
  await page.getByLabel("Временный токен гостя").fill(token);
  await page.getByRole("button", { name: "Подключиться", exact: true }).click();
  await expect(page.getByRole("button", { name: "Заселиться" })).toBeVisible();
}
async function navigate(page: import("@playwright/test").Page, item: string) {
  await page.getByRole("button", { name: "Меню" }).click();
  await page.getByRole("navigation").getByRole("button", { name: item, exact: true }).click();
}

test("Stage 4: planning warnings are immediately perceivable on mobile and desktop", async ({ page, request }) => {
  await page.route("**/api/v1/prepared", async (route) => {
    const response = await route.fetch();
    const prepared = await response.json();
    prepared.explanations = [...(prepared.explanations ?? []), {
      device_id: "light",
      status: "warning",
      source: "rules",
      reason: "R6: проверка допустимого света перед сном",
    }];
    await route.fulfill({ response, json: prepared });
  });
  await connect(page, request);
  await page.getByRole("button", { name: "Заселиться" }).click();
  const warning = page.getByRole("alert", { name: "Предупреждения сценария" });
  await expect(warning).toBeVisible();
  await expect(warning).toContainText("R6: проверка допустимого света перед сном");
  await page.setViewportSize({ width: 1440, height: 900 });
  await expect(warning).toBeVisible();
  await expect(warning).toContainText("R6:");
});

test("Stage 4: uncertain transport error has no illustrative pseudo-Retry button", async ({ page, request }) => {
  await page.route("**/api/v1/messages", (route) => route.abort("failed"));
  await connect(page, request);
  await navigate(page, "Диалог");
  await page.getByRole("textbox", { name: "Просьба" }).fill("Сделай попрохладнее");
  await page.getByRole("button", { name: "Отправить просьбу" }).click();
  const error = page.locator(".delivery-error");
  await expect(error).toBeVisible();
  await expect(error).toContainText("Перед повторной командой проверьте состояние номера.");
  await expect(error.getByRole("button", { name: "Повторить" })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Отправить просьбу" })).toBeDisabled();
});

test("Stage 4: climate uses confirmed-action Save instead of static Applied artwork", async ({ page, request }) => {
  await connect(page, request);
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

test("Stage 4: core mobile controls remain scroll-reachable at 320x568", async ({ page, request }) => {
  await page.setViewportSize({ width: 320, height: 568 });
  await connect(page, request);
  await navigate(page, "Диалог");
  const composer = page.getByRole("textbox", { name: "Просьба" });
  await expect(composer).toBeVisible();
  await composer.scrollIntoViewIfNeeded();
  await expect(composer).toBeInViewport();
  const width = await page.evaluate(() => document.documentElement.scrollWidth);
  expect(width).toBeLessThanOrEqual(321);
});
