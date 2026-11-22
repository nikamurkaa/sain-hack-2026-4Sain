import { expect, test } from "@playwright/test";
import { mkdirSync } from "node:fs";
import type { APIRequestContext, Page } from "@playwright/test";

const host = "http://127.0.0.1:8765";
const T1 = "2026-11-12T20:00:00+03:00";
const T2 = "2026-11-12T20:45:00+03:00";

async function connect(page: Page, request: APIRequestContext) {
  const opened = await request.post(host + "/api/v1/sessions", {
    headers: { Authorization: "Bearer offline-team" },
    data: { source: "dev", stay_id: "stay_test" },
  });
  expect(opened.status()).toBe(201);
  const token = (await opened.json()).session_token as string;
  await page.goto("/");
  await page.getByLabel("Временный токен гостя").fill(token);
  await page.getByRole("button", { name: "Подключиться", exact: true }).click();
  await expect(page.getByRole("button", { name: "Заселиться" })).toBeVisible();
  await page.getByRole("button", { name: "Меню" }).click();
  await page.getByRole("navigation").getByRole("button", { name: "Диалог", exact: true }).click();
  return token;
}
async function close(request: APIRequestContext, token: string) {
  await request.delete(host + "/api/v1/session", {
    headers: { Authorization: "Bearer " + token },
  });
}

for (const size of [
  { width: 375, height: 812, name: "mobile" },
  { width: 1440, height: 900, name: "desktop" },
]) {
  test("MR-NEW-04: REAL cancelled upstream POST T2 -> stale GET -> reconnect -> safe T2 " + size.name,
    async ({page,request,browserName}) => {
    await page.setViewportSize({width:size.width,height:size.height});
    const token=await connect(page,request);
    let browserPosts=0;
    let firstKey="";
    page.on("request",async r=>{
      if(r.url().endsWith("/api/v1/messages")&&r.method()==="POST") {
        browserPosts++;
        if(browserPosts===1) firstKey=(await r.allHeaders())["idempotency-key"];
      }
    });
    let intercepted=0;
    await page.route("**/api/v1/messages",async route=>{
      const body=route.request().postDataJSON() as {at:string;text:string};
      if(intercepted++===0) {
        expect(body.at).toBe(T1);
        await route.continue({postData:JSON.stringify({...body,at:T2})});
      } else {
        await route.continue();
      }
    });
    try {
      await page.getByRole("textbox",{name:"Просьба",exact:true}).fill("Проверка отмены после принятия");
      await page.getByRole("button",{name:"Отправить просьбу"}).click();
      const panel=page.locator('[data-action-kind="uncertain"]');
      await expect(panel).toBeVisible({timeout:20000});
      await expect(panel).toContainText("Результат просьбы пока неизвестен");
      await expect(panel).toContainText("20:45");
      await expect(panel.getByRole("status")).toContainText("не подтверждено");
      await expect(panel.getByRole("button",{name:"Закрыть уведомление"})).toBeDisabled();
      const auth={Authorization:"Bearer "+token};
      const live=await request.get(host+"/api/v1/state",{headers:auth,params:{at:T2}});
      expect(live.status()).toBe(200);
      expect((await live.json()).state.light.brightness).toBe(0);
      const early=await request.post(host+"/api/v1/devices",{
        headers:{...auth,"Idempotency-Key":"mrnew04-e2e-past"},
        data:{at:T1,device_id:"light",values:{brightness:30}},
      });
      expect(early.status()).toBe(409);
      expect((await early.json()).code).toBe("RECOVERY_REQUIRED");
      const session=await request.get(host+"/api/v1/session",{headers:auth});
      expect(session.status()).toBe(200);
      const info=await session.json();
      expect(info.reconciliation_required).toBe(true);
      expect(info.pending_action.attempted_at).toBe(T2);
      expect(info.pending_action.code).toBe("ACTION_UNCERTAIN");
      expect(browserPosts).toBe(1);
      expect(firstKey.length).toBeGreaterThan(8);
      const replay=await request.post(host+"/api/v1/messages",{
        headers:{...auth,"Idempotency-Key":firstKey},
        data:{at:T2,text:"Проверка отмены после принятия"},
      });
      expect(replay.status()).toBe(409);
      expect((await replay.json()).operation_id).toBe(info.pending_action.operation_id);
      expect(browserPosts).toBe(1);
      const typed=page.getByRole("textbox",{name:"Просьба",exact:true});
      await typed.fill("Сделай попрохладнее");
      await expect(page.getByRole("button",{name:"Отправить просьбу"})).toBeDisabled();
      mkdirSync("evidence",{recursive:true});
      await page.screenshot({path:`evidence/mrnew04-cancelled-${browserName}-${size.name}.png`,fullPage:true});

      // Losing the HTTP response must not make the operation disappear from
      // the in-memory session. Reauth with the same still valid guest token.
      await page.reload();
      await page.getByLabel("Временный токен гостя").fill(token);
      await page.getByRole("button",{name:"Подключиться",exact:true}).click();
      const resumed=page.locator('[data-action-kind="uncertain"]');
      await expect(resumed).toBeVisible();
      await expect(resumed.getByRole("button",{name:"Закрыть уведомление"})).toBeDisabled();
      await resumed.getByRole("button",{name:"Обновить состояние номера"}).click();
      await expect(resumed.getByRole("status")).toContainText("Фактическое состояние получено");
      await resumed.getByRole("button",{name:"Закрыть уведомление"}).click();
      await page.getByRole("textbox",{name:"Просьба",exact:true}).fill("Сделай попрохладнее");
      const next=page.waitForResponse(r=>r.url().endsWith("/api/v1/messages")&&r.request().method()==="POST"&&r.status()===200);
      await page.getByRole("button",{name:"Отправить просьбу"}).click();
      await next;
      expect(browserPosts).toBe(2); // only explicit safe T2 action after verified GET
    } finally {await close(request,token);}
  });
}
