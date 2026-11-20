import { test, expect } from "@playwright/test";
import type { Page } from "@playwright/test";
import { readFileSync, mkdirSync, writeFileSync } from "node:fs";
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
  guest.profile.display_name = "Алиса";
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
        stay_id: "Номер 412",
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
  if (typeof name === "number") {
    await expect(page.locator(".design-frame")).toHaveAttribute(
      "data-frame",
      String(name),
    );
  }
  if (!process.env.SAIN_SCREENSHOTS) return;
  const dir = process.env.SAIN_SCREENSHOTS;
  mkdirSync(dir, { recursive: true });
  await page.evaluate(async () => {
    await document.fonts.ready;
    const images = Array.from(document.images);
    for (const node of document.querySelectorAll<SVGImageElement>(
      ".design-defs image",
    )) {
      const img = new Image();
      img.src = node.href.baseVal;
      images.push(img);
    }
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
    await new Promise(requestAnimationFrame);
    await new Promise(requestAnimationFrame);
  });
  if (typeof name === "number" && process.env.SAIN_DESKTOP_SHOTS) {
    const covered = await page.evaluate(() =>
      Array.from(
        document.querySelectorAll<HTMLElement>(
          "button:not(:disabled),input:not(:disabled),select:not(:disabled),textarea:not(:disabled)",
        ),
      ).flatMap((el) => {
        const r = el.getBoundingClientRect(),
          x = r.left + r.width / 2,
          y = r.top + r.height / 2;
        if (!r.width || !r.height || y < 0 || y >= innerHeight) return [];
        return el.contains(document.elementFromPoint(x, y))
          ? []
          : [el.getAttribute("aria-label") || el.textContent || el.tagName];
      }),
    );
    writeFileSync(
      dir + "/" + String(name).padStart(2, "0") + "-hit.json",
      JSON.stringify(covered),
    );
  }
  if (process.env.SAIN_DESKTOP_SHOTS && typeof name === "number") {
    const desktop = process.env.SAIN_DESKTOP_SHOTS;
    mkdirSync(desktop, { recursive: true });
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.evaluate(() => new Promise(requestAnimationFrame));
    await page.screenshot({
      path: desktop + "/" + String(name).padStart(2, "0") + ".png",
      animations: "disabled",
    });
    await page.setViewportSize({ width: 375, height: 812 });
    await expect(page.locator(".design-frame")).toHaveAttribute(
      "data-frame",
      String(name),
    );
  }
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
    await expect(
      page.getByRole("heading", { name: /Ваш план/i }),
    ).toBeVisible();
    await shot(page, i * 2 + 1);
    await page.getByText("В номер", { exact: true }).click();
    await expect(page.locator(".hero-card")).toContainText(
      ["Утренний режим", "Дневной режим", "Вечерний режим", "Ночной режим"][i],
    );
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
  c.loading = process.env.SAIN_DESKTOP_SHOTS ? 2400 : 800;
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
  c.delay = process.env.SAIN_DESKTOP_SHOTS ? 1600 : 700;
  await page.getByText("Сделай попрохладнее", { exact: true }).click();
  await expect(page.getByText("Выполняю просьбу…")).toBeVisible();
  await shot(page, 25);
  await expect(page.locator(".reply.done")).toBeVisible();
  await shot(page, 10);
  await page.getByLabel("Просьба", { exact: true }).fill("Ещё немного");
  await page.getByLabel("Отправить просьбу").click();
  await shot(page, 26);
  await page.getByLabel("Просьба", { exact: true }).fill("Поставь 35 градусов");
  await page.getByLabel("Отправить просьбу").click();
  await expect(page.locator(".refused")).toBeVisible();
  await shot(page, 27);
  c.fail = true;
  await page.getByLabel("Просьба", { exact: true }).fill("Сделай попрохладнее");
  await page.getByLabel("Отправить просьбу").click();
  await expect(page.getByRole("alert")).toBeVisible();
  await shot(page, 28);
  await page.getByRole("button", { name: "Закрыть", exact: true }).click();
  c.fail = false;
  c.stt = process.env.SAIN_DESKTOP_SHOTS ? 2400 : 850;
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

test("first refusal and unknown delivery have their own layouts", async ({
  page,
}) => {
  const c = await fixture(page, hours[0]);
  await start(page);
  await expect(page.getByText("Заселиться")).toBeVisible();
  await go(page, "Диалог");
  c.fail = true;
  await page.getByLabel("Просьба", { exact: true }).fill("Сделай прохладнее");
  await page.getByLabel("Отправить просьбу").click();
  await shot(page, 16);
  await page.getByRole("button", { name: "Закрыть", exact: true }).click();
  c.fail = false;
  await page.getByLabel("Просьба", { exact: true }).fill("Поставь 35 градусов");
  await page.getByLabel("Отправить просьбу").click();
  await shot(page, 15);
});
