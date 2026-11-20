import { test, expect } from "@playwright/test";
import type { Page } from "@playwright/test";
import { readFileSync, mkdirSync } from "node:fs";
const sample = (name: string) =>
  JSON.parse(readFileSync("../docs/examples/room/" + name + ".json", "utf8"));
const catalog = JSON.parse(readFileSync("../tests/catalog.json", "utf8"));
const names = ["Утро", "День", "Вечер", "Ночь"];
const hours = ["07:12", "14:37", "19:48", "23:01"];
const stamp = (hh: string) => "2026-11-12T" + hh + ":00+03:00";
const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));
async function fixture(page: Page, hour: string) {
  let state = sample("state").state;
  const guest = sample("guest");
  guest.stay.check_in_at = stamp("00:00");
  const controls = { fail: false, expire: false, delay: 0, stt: 0, loading: 0 };
  await page.route("**/api/v1/**", async (r) => {
    const url = new URL(r.request().url()),
      route = url.pathname.split("/").pop();
    let data: unknown;
    let status = 200;
    if (route === "session") {
      await sleep(controls.loading);
      data = {
        source: "dev",
        actions: ["state", "message", "transcription"],
        read_only: false,
        can_send_requests: true,
        expires_in: 2400,
        at: stamp(hour),
        until: stamp("23:59"),
        history: [],
        stay_id: "stay_demo",
        connection_status: "available",
      };
    }
    if (route === "prepared")
      data = { guest, scenario: sample("scenario"), last_confirmed: null };
    if (route === "catalog") data = catalog;
    if (route === "state")
      data = { at: url.searchParams.get("at") ?? stamp(hour), state };
    if (route === "messages") {
      await sleep(controls.delay);
      if (controls.expire) {
        status = 401;
        data = {};
      } else if (controls.fail) {
        await r.abort();
        return;
      } else if (r.request().postDataJSON().text.includes("35"))
        data = {
          reply: {
            text: "Допустимая температура в номере — 16–26 °C.",
            response_class: "refused",
          },
          state,
        };
      else {
        const result = sample("message");
        state = result.state;
        data = result;
      }
    }
    if (route === "transcriptions") {
      await sleep(controls.stt);
      data = { text: "Сделай попрохладнее" };
    }
    await r.fulfill({ status, json: data });
  });
  return controls;
}
async function start(page: Page) {
  await page.goto("/");
  await page
    .getByLabel("Временный токен гостя")
    .fill("synthetic-visual-session");
  await page.getByRole("button", { name: "Подключиться" }).click();
}
async function go(page: Page, name: string) {
  await page.getByLabel("Меню").click();
  await page.getByRole("navigation").getByText(name, { exact: true }).click();
}
async function shot(page: Page, name: string | number) {
  if (!process.env.SAIN_SCREENSHOTS) return;
  const dir = process.env.SAIN_SCREENSHOTS;
  mkdirSync(dir, { recursive: true });
  await page.evaluate(async () => {
    await document.fonts.ready;
    const images = Array.from(document.images);
    for (const el of document.querySelectorAll(".hero,.wave,.ended")) {
      for (const match of getComputedStyle(el).backgroundImage.matchAll(
        /url\("([^"]+)"\)/g,
      )) {
        const img = new Image();
        img.src = match[1];
        images.push(img);
      }
    }
    await Promise.all(images.map((i) => i.decode()));
  });
  await page.screenshot({
    path: dir + "/" + String(name).padStart(2, "0") + ".png",
    animations: "disabled",
  });
}
for (let i = 0; i < 4; i++)
  test("period " + names[i], async ({ page }) => {
    await fixture(page, hours[i]);
    await start(page);
    await page.getByText("Заселиться").click();
    await expect(page.getByRole("heading", { name: /Ваш план/ })).toBeVisible();
    await shot(page, i * 2 + 1);
    await page.getByText("В номер", { exact: true }).click();
    await expect(page.locator(".hero strong")).toHaveText(names[i]);
    await shot(page, i * 2 + 2);
    await go(page, "Виртуальное время");
    await page.getByRole("button", { name: names[i], exact: true }).click();
    await expect(page.locator(".rows")).toContainText("22 °C");
    await shot(page, 17 + i);
  });
test("connection, device settings, chat lifecycle, voice review and expiry", async ({
  page,
}) => {
  const c = await fixture(page, "19:48");
  c.loading = 800;
  await start(page);
  await expect(page.getByRole("status")).toContainText("Загружаем");
  await shot(page, 24);
  await expect(page.getByText("Заселиться")).toBeVisible();
  await shot(page, 11);
  for (const [offset, device] of ["Климат", "Будильник", "Звук"].entries()) {
    await go(page, "Мой номер");
    await page.locator(".device").filter({ hasText: device }).click();
    await expect(
      page.getByRole("heading", { name: device, exact: true }),
    ).toBeVisible();
    await shot(page, 21 + offset);
  }
  await go(page, "Диалог");
  await shot(page, 9);
  c.delay = 700;
  await page.getByText("Сделай попрохладнее", { exact: true }).click();
  await expect(page.getByText("Выполняю просьбу…")).toBeVisible();
  await shot(page, 25);
  await expect(page.locator(".reply.done")).toBeVisible();
  await shot(page, 10);
  await shot(page, 26);
  await page.getByLabel("Просьба", { exact: true }).fill("Поставь 35 градусов");
  await page.getByLabel("Отправить просьбу").click();
  await expect(page.locator(".refused")).toBeVisible();
  await shot(page, 15);
  await shot(page, 27);
  c.fail = true;
  await page.getByLabel("Просьба", { exact: true }).fill("Сделай попрохладнее");
  await page.getByLabel("Отправить просьбу").click();
  await expect(page.getByRole("alert")).toBeVisible();
  await shot(page, 16);
  await shot(page, 28);
  await page.getByRole("button", { name: "Закрыть", exact: true }).click();
  c.fail = false;
  c.stt = 850;
  await page.getByLabel("Голосовой ввод").click();
  await expect(page.locator(".record")).toBeVisible();
  await shot(page, 12);
  await page.waitForTimeout(550);
  await page.locator(".record").click();
  await expect(
    page.getByRole("heading", { name: "Распознаём вашу команду" }),
  ).toBeVisible();
  await shot(page, 13);
  await expect(page.getByLabel("Распознанный текст")).toBeVisible();
  await shot(page, 14);
  await page.getByRole("button", { name: "Отменить" }).click();
  await go(page, "Мой номер");
  for (const width of [768, 1440]) {
    await page.setViewportSize({ width, height: 900 });
    await shot(page, "room-" + width);
  }
  await page.setViewportSize({ width: 375, height: 812 });
  await go(page, "Диалог");
  c.expire = true;
  await page.getByLabel("Просьба", { exact: true }).fill("Прохладнее");
  await page.getByLabel("Отправить просьбу").click();
  await expect(page.getByText("Сеанс завершён")).toBeVisible();
  await shot(page, 29);
});
