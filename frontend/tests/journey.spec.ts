import { expect, test } from "@playwright/test";
import type { Page, APIRequestContext } from "@playwright/test";
async function connect(page: Page, request: APIRequestContext, source = "dev") {
  const res = await request.post("http://127.0.0.1:8765/api/v1/sessions", {
    headers: { Authorization: "Bearer offline-team" },
    data: { source, stay_id: "stay_test" },
  });
  expect(res.status()).toBe(201);
  await page.goto("/");
  await page
    .getByLabel("Временный токен гостя")
    .fill((await res.json()).session_token);
  await page.getByRole("button", { name: "Подключиться", exact: true }).click();
  await expect(page.getByRole("button", { name: "Заселиться" })).toBeVisible();
}
async function go(page: Page, label: string) {
  await page.getByRole("button", { name: "Меню" }).click();
  await page
    .getByRole("navigation")
    .getByRole("button", { name: label, exact: true })
    .click();
}
async function say(page: Page, text: string) {
  await page.getByRole("textbox", { name: "Просьба", exact: true }).fill(text);
  await page.getByRole("button", { name: "Отправить просьбу" }).click();
}
const climate = (page: Page) =>
  page.locator(".devices .device").filter({ hasText: "Климат" });
test("check-in, real API, contextual chat, refusal and unknown delivery", async ({
  page,
  request,
}) => {
  await connect(page, request);
  await page.getByText("Заселиться").click();
  await page.getByRole("button", { name: "День", exact: true }).click();
  await expect(
    page.getByText("На этот период действий в расписании нет."),
  ).toBeVisible();
  await page.getByText("В номер", { exact: true }).click();
  await go(page, "Диалог");
  const initial = Number(
    (await climate(page).locator("strong").innerText()).split(" ")[0],
  );
  await page.getByRole("button", { name: "Сделай попрохладнее" }).click();
  await expect(climate(page)).toContainText(initial - 1 + " °C");
  await say(page, "Ещё немного");
  await expect(climate(page)).toContainText(initial - 2 + " °C");
  await say(page, "Поставь 35 градусов");
  await expect(page.locator(".refused")).toBeVisible();
  await expect(climate(page)).toContainText(initial - 2 + " °C");
  const keys: string[] = [];
  await page.route("**/api/v1/messages", async (route) => {
    keys.push(route.request().headers()["idempotency-key"]);
    if (keys.length === 1) {
      await route.fetch();
      await route.abort();
    } else await route.continue();
  });
  await say(page, "Сделай попрохладнее");
  await page.getByRole("button", { name: "Повторить", exact: true }).click();
  await expect(climate(page)).toContainText(initial - 3 + " °C");
  await expect(page.getByRole("alert")).toHaveCount(0);
  expect(keys).toHaveLength(2);
  expect(keys[0]).toBe(keys[1]);
  await expect(page.locator(".exchange")).toHaveCount(4);
});
test("confirmed voice with browser capture and fake STT", async ({
  page,
  request,
}) => {
  await connect(page, request);
  await go(page, "Диалог");
  let commands = 0;
  page.on("request", (r) => {
    if (r.url().endsWith("/messages")) commands++;
  });
  await page.getByLabel("Голосовой ввод").click();
  const stop = page
    .getByRole("button", { name: "Завершить запись", exact: true })
    .last();
  await expect(stop).toBeVisible();
  await page.waitForTimeout(700);
  await stop.click();
  await expect(page.getByLabel("Распознанный текст")).toHaveValue(
    "Сделай попрохладнее",
  );
  expect(commands).toBe(0);
  await page.getByRole("button", { name: "Отправить", exact: true }).click();
  await expect(page.locator(".reply.done")).toBeVisible();
  expect(commands).toBe(1);
});
test("final snapshot, virtual reads, isolation and expiry", async ({
  page,
  request,
}) => {
  await connect(page, request, "final");
  await expect(page.getByText("Финальный гость · просмотр")).toBeVisible();
  await go(page, "Профиль гостя");
  await expect(page.getByText(/final_test/)).toBeVisible();
  await go(page, "Виртуальное время");
  await page.getByRole("button", { name: "Ночь", exact: true }).click();
  await expect(page.locator(".rows").getByText("0 %")).toBeVisible();
  await expect(
    page.getByRole("button", { name: "День", exact: true }),
  ).toBeDisabled();
  await go(page, "Диалог");
  await expect(page.getByLabel("Голосовой ввод")).toHaveCount(0);
  await go(page, "Сменить сеанс");
  await connect(page, request);
  await page.route("**/api/v1/messages", (r) =>
    r.fulfill({ status: 401, body: "{}" }),
  );
  await go(page, "Диалог");
  await page.getByRole("button", { name: "Сделай попрохладнее" }).click();
  await expect(page.getByText("Сеанс завершён")).toBeVisible();
  await page.getByText("Переподключиться").click();
  await expect(
    page.getByText("Демонстрационный номер · управление"),
  ).toBeVisible();
});
test("responsive layouts and confirmed manual climate", async ({
  page,
  request,
}) => {
  await connect(page, request);
  await go(page, "Мой номер");
  for (const width of [320, 360, 375, 390, 430, 768, 1024, 1280, 1440, 1920]) {
    await page.setViewportSize({ width, height: 812 });
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBeTruthy();
  }
  await climate(page).click();
  await page.getByRole("spinbutton").fill("21");
  await page.getByRole("button", { name: "Сохранить" }).click();
  await expect(climate(page)).toContainText("21 °C");
});
test("read-only final survives loss of live readings", async ({
  page,
  request,
}) => {
  await page.route("**/api/v1/state*", (r) =>
    r.fulfill({ status: 403, json: {} }),
  );
  await connect(page, request, "final");
  await expect(page.getByText("Живое состояние недоступно")).toBeVisible();
  await page.getByText("Заселиться").click();
  await expect(page.locator(".timeline article").first()).toBeVisible();
  await go(page, "Виртуальное время");
  await expect(page.getByRole("alert")).toContainText("Нет доступа");
  await page.getByText("Посмотреть план").click();
  await expect(page.locator(".timeline")).toBeVisible();
});
test("standalone server restricts privileged routes and keeps tokens out of browser storage", async ({
  page,
  request,
}) => {
  expect(
    (
      await request.post("/api/v1/sessions", { data: { source: "dev" } })
    ).status(),
  ).toBe(404);
  expect(
    (
      await request.post("/api/v1/messages", {
        headers: { Origin: "https://untrusted.invalid" },
        data: {},
      })
    ).status(),
  ).toBe(403);
  const urls: string[] = [];
  page.on("request", (r) => urls.push(r.url()));
  await connect(page, request);
  expect(
    await page.evaluate(() => [
      localStorage.length,
      sessionStorage.length,
      document.cookie,
    ]),
  ).toEqual([0, 0, ""]);
  expect(
    urls.every((url) => new URL(url).origin === "http://127.0.0.1:4173"),
  ).toBe(true);
  expect(urls.every((url) => !/(token|Bearer|\/sessions)/i.test(url))).toBe(
    true,
  );
});
