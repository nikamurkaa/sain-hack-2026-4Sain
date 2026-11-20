import { expect, test } from "@playwright/test";
import type { Page, APIRequestContext } from "@playwright/test";
const issued = new Set<string>();
test.afterEach(async ({ request }) => {
  for (const token of issued)
    await request.delete("http://127.0.0.1:8765/api/v1/session", {
      headers: { Authorization: "Bearer " + token },
    });
  issued.clear();
});
async function connect(page: Page, request: APIRequestContext, source = "dev") {
  const res = await request.post("http://127.0.0.1:8765/api/v1/sessions", {
    headers: { Authorization: "Bearer offline-team" },
    data: source === "final" ? { source } : { source, stay_id: "stay_test" },
  });
  expect(res.status()).toBe(201);
  const token = (await res.json()).session_token;
  issued.add(token);
  await page.goto("/");
  await page.getByLabel("Временный токен гостя").fill(token);
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
  page.locator(".device").filter({ hasText: "Климат" });
test("check-in, real API, contextual chat, refusal and unknown delivery", async ({
  page,
  request,
}) => {
  await connect(page, request);
  await page.getByText("Заселиться").click();
  await page.getByRole("button", { name: "День", exact: true }).click();
  await expect(
    page.getByText("В этот период автоматических изменений не запланировано."),
  ).toBeVisible();
  await page.getByText("В номер", { exact: true }).click();
  await go(page, "Диалог");
  const initial = Number(
    (await climate(page).locator(".design-label").last().innerText()).split(
      " ",
    )[0],
  );
  await page.getByRole("button", { name: "Сделай попрохладнее" }).click();
  await expect(climate(page)).toContainText(initial - 1 + " °C");
  await say(page, "Ещё немного");
  await expect(climate(page)).toContainText(initial - 2 + " °C");
  await say(page, "Ещё немного");
  await expect(climate(page)).toContainText(initial - 3 + " °C");
  await say(page, "Поставь 35 градусов");
  await expect(page.locator(".refused")).toBeVisible();
  await expect(climate(page)).toContainText(initial - 3 + " °C");
  const keys: string[] = [];
  await page.route("**/api/v1/messages", async (route) => {
    keys.push(route.request().headers()["idempotency-key"]);
    if (keys.length === 1) {
      await route.fetch();
      await route.abort();
    } else await route.continue();
  });
  await say(page, "Сделай попрохладнее");
  // The server confirms delivery via authoritative history: no duplicate action.
  await expect(climate(page)).toContainText(initial - 4 + " °C");
  await expect(page.getByRole("alert")).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Повторить", exact: true })).toHaveCount(0);
  expect(keys).toHaveLength(1);
  await page
    .getByRole("button", { name: "Диалог · История сообщений" })
    .click();
  await expect(page.locator(".exchange")).toHaveCount(5);
});
test("confirmed voice with browser capture and fake STT", async ({
  page,
  request,
}) => {
  await connect(page, request);
  await go(page, "Диалог");
  test.skip(
    await page.evaluate(
      () =>
        !navigator.mediaDevices?.getUserMedia ||
        typeof MediaRecorder === "undefined",
    ),
    "This browser build has no audio capture API.",
  );
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
  await page.getByLabel("Распознанный текст").fill("Душно");
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
  await page.getByText("Технические сведения о проживании").click();
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
    page.getByText("Демо-номер · управление"),
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

test("all manual settings commit confirmed values and all four dev previews read the API", async ({
  page,
  request,
}) => {
  await connect(page, request);
  const settings = [
    ["Климат", "21", "temperature_c", "climate"],
    ["Свет", "38", "brightness", "light"],
    ["Шторы", "65", "position", "curtains"],
    ["Звук", "42", "volume", "sound"],
    ["Звук", "track_04", "track_id", "sound"],
    ["Будильник", "06:40", "at", "alarm"],
    ["Не беспокоить", "true", "enabled", "dnd"],
  ];
  for (const [name, value, field, id] of settings) {
    await go(page, "Мой номер");
    await page.getByRole("button", { name, exact: true }).click();
    if (field === "track_id")
      await page.getByLabel("Трек", { exact: true }).selectOption(value);
    else if (id === "sound")
      await page.getByRole("slider", { name: "Громкость" }).fill(value);
    else if (id === "alarm")
      await page.getByLabel("Время пробуждения").fill(value);
    else if (id === "dnd") await page.getByRole("combobox").selectOption(value);
    else await page.getByRole("spinbutton").fill(value);
    const result = page.waitForResponse((r) => r.url().endsWith("/devices"));
    await page.getByRole("button", { name: /^Сохранить/ }).click();
    const data = await (await result).json();
    expect(data.reply.response_class).toBe("done");
    expect(String(data.state[id][field])).toContain(value);
    await expect(page.locator(".reply.done")).toBeVisible();
  }
  await go(page, "Виртуальное время");
  await expect(page.locator(".rows")).toContainText("°C");
  for (const name of ["Утро", "День", "Вечер", "Ночь"]) {
    const read = page.waitForResponse((r) => r.url().includes("/state?at="));
    await page.getByRole("button", { name, exact: true }).click();
    const data = await (await read).json();
    await expect(page.locator(".rows")).toContainText(
      data.state.climate.temperature_c + " °C",
    );
  }
});
test("denied microphone gives an accessible message and keeps typed requests available", async ({
  page,
  request,
}) => {
  await page.addInitScript(() => {
    if (!navigator.mediaDevices) return;
    Object.defineProperty(navigator.mediaDevices, "getUserMedia", {
      value: async () => {
        throw new DOMException("Denied", "NotAllowedError");
      },
    });
  });
  await connect(page, request);
  await go(page, "Диалог");
  await page.getByLabel("Голосовой ввод").click();
  const supported = await page.evaluate(
    () =>
      !!navigator.mediaDevices?.getUserMedia &&
      typeof MediaRecorder !== "undefined",
  );
  await expect(page.getByRole("alert")).toContainText(
    supported ? "Разрешите доступ" : "Запись недоступна",
  );
  await page.getByRole("button", { name: "Отменить" }).click();
  await say(page, "Сделай попрохладнее");
  await expect(page.locator(".reply.done")).toBeVisible();
});

test("browser history, double submit, in-flight session switch, resize and refresh", async ({
  page,
  request,
  context,
}) => {
  await connect(page, request);
  await page.getByText("Заселиться", { exact: true }).click();
  await page.getByText("В номер", { exact: true }).click();
  await page.goBack();
  await expect(page.locator(".personal-plan")).toBeVisible();
  await page.goForward();
  await expect(climate(page)).toBeVisible();
  await go(page, "Диалог");
  const input = page.getByLabel("Просьба", { exact: true });
  await expect(page.getByLabel("Отправить просьбу")).toBeDisabled();
  await input.fill("Сделай попрохладнее");
  let count = 0;
  let release!: () => void;
  const paused = new Promise<void>((resolve) => {
    release = resolve;
  });
  await page.route("**/messages", async (r) => {
    count++;
    await paused;
    await r.continue();
  });
  await input.press("Enter");
  await input
    .press("Enter", { noWaitAfter: true, timeout: 500 })
    .catch(() => {});
  await page.getByRole("button", { name: "Меню", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "Сменить сеанс" }),
  ).toBeDisabled();
  await page.setViewportSize({ width: 1440, height: 900 });
  release();
  await expect(page.locator(".reply.done")).toBeVisible();
  expect(count).toBe(1);
  const another = await context.newPage();
  await another.goto("/");
  await expect(another.getByLabel("Временный токен гостя")).toBeVisible();
  await page.reload();
  await expect(page.getByLabel("Временный токен гостя")).toBeVisible();
});
