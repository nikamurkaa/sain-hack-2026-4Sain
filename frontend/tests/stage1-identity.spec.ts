import { test, expect } from "@playwright/test";

test("S-010: official guest dataset never invents an identity on virtual screen", async ({ page, request }) => {
  const opened = await request.post("http://127.0.0.1:8765/api/v1/sessions", {
    headers: { Authorization: "Bearer offline-team" },
    data: { source: "dev", stay_id: "stay_test" },
  });
  expect(opened.status()).toBe(201);
  const token = (await opened.json()).session_token;
  try {
    const prepared = await request.get("http://127.0.0.1:8765/api/v1/prepared", {
      headers: { Authorization: "Bearer " + token },
    });
    expect(prepared.status()).toBe(200);
    expect((await prepared.json()).guest.profile.display_name).toBeUndefined();
    await page.goto("/");
    await page.getByLabel("Временный токен гостя").fill(token);
    await page.getByRole("button", { name: "Подключиться", exact: true }).click();
    await expect(page.getByRole("button", { name: "Заселиться" })).toBeVisible();
    await page.getByRole("button", { name: "Меню" }).click();
    await page.getByRole("navigation").getByRole("button", { name: "Виртуальное время" }).click();
    await expect(page.getByRole("heading", { name: "Алина," })).toHaveCount(0);
    await expect(page.getByRole("heading", { name: "Ваш номер" })).toBeVisible();
  } finally {
    await request.delete("http://127.0.0.1:8765/api/v1/session", {
      headers: { Authorization: "Bearer " + token },
    });
  }
});
