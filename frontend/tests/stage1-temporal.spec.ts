import { expect, test } from "@playwright/test";
import { mkdirSync } from "node:fs";
import type { Page, APIRequestContext } from "@playwright/test";

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
async function send(page: Page, text: string) {
  await page.getByRole("textbox", { name: "Просьба", exact: true }).fill(text);
  const received = page.waitForResponse(r =>
    r.url().endsWith("/api/v1/messages") && r.request().method() === "POST");
  await page.getByRole("button", { name: "Отправить просьбу" }).click();
  return received;
}
async function cleanup(request: APIRequestContext, token: string) {
  await request.delete(host + "/api/v1/session",
    { headers: { Authorization: "Bearer " + token } });
}

for (const [width, height, label] of [[375,812,"mobile"],[1440,900,"desktop"]] as const) {
  test("MR-NEW-01 actual future T2 partial -> operation reconciliation -> safe next action " + label,
    async ({page,request,browserName}) => {
    await page.setViewportSize({width,height});
    const token = await connect(page,request);
    let posts=0, rewritten=0;
    let nextAt: string | undefined;
    page.on("request",r => {
      if(r.url().endsWith("/api/v1/messages") && r.method()==="POST") {
        posts++;
        if(posts>1) nextAt=(r.postDataJSON() as {at:string}).at;
      }
    });
    await page.route("**/api/v1/messages",async route=>{
      if(rewritten++===0){
        const body=route.request().postDataJSON() as {at:string;text:string};
        expect(body.at).toBe(T1);
        await route.continue({postData:JSON.stringify({...body,at:T2})});
      } else await route.continue();
    });
    try {
      const partial = await send(page,"Проверка частичного выполнения");
      expect(partial.status()).toBe(409);
      const data=await partial.json();
      expect(data.code).toBe("ACTION_PARTIAL");
      expect(data.attempted_at).toBe(T2);
      const panel=page.locator('[data-action-kind="partial"]');
      await expect(panel).toBeVisible();
      await expect(panel).toContainText("20:45");
      await expect(panel.getByRole("status")).toContainText("Фактическое состояние получено");
      const before=await request.get(host+"/api/v1/state",
        {headers:{Authorization:"Bearer "+token}});
      expect((await before.json()).at).toBe(T1);
      expect((await before.json()).state.light.brightness).toBe(70);
      const atT2=await request.get(host+"/api/v1/state",
        {headers:{Authorization:"Bearer "+token}, params:{at:T2}});
      expect((await atT2.json()).state.light.brightness).toBe(0);
      const recovered=await request.get(host+"/api/v1/reconciliation",
        {headers:{Authorization:"Bearer "+token},params:{operation_id:data.operation_id}});
      expect(recovered.status()).toBe(200);
      expect((await recovered.json()).snapshot.at).toBe(T2);
      const manualOld=await request.post(host+"/api/v1/devices",{
        headers:{Authorization:"Bearer "+token,"Idempotency-Key":"mrnew01-e2e-early"},
        data:{device_id:"light",values:{brightness:40},at:T1},
      });
      expect(manualOld.status()).toBe(409);
      expect((await manualOld.json()).code).toBe("TIME_BACKWARDS");
      expect(posts).toBe(1);
      mkdirSync("evidence",{recursive:true});
      await page.screenshot({path:`evidence/mrnew01-t2-${browserName}-${label}.png`,fullPage:true});
      await panel.getByRole("button",{name:"Закрыть уведомление"}).click();
      const result=await send(page,"Сделай попрохладнее");
      expect(result.status()).toBe(200);
      expect(nextAt).toBe(T2);
      expect(posts).toBe(2);
    } finally {await cleanup(request,token);}
  });
}

test("MR-NEW-01 stale HTTP 200 at T1 MUST NOT authorize T2 outcome, then correct offset may reconcile",
  async ({page,request}) => {
  const token=await connect(page,request);
  let uses=0;
  let posts=0;
  page.on("request",r=>{if(r.url().endsWith("/api/v1/messages")&&r.method()==="POST")posts++;});
  await page.route("**/api/v1/reconciliation?*",async route=>{
    uses++;
    const result=await route.fetch();
    const json=await result.json();
    if(uses===1){
      await route.fulfill({status:200,json:{
        ...json,snapshot:{...json.snapshot,at:T1},
      }});
    } else {
      await route.fulfill({status:200,json:{
        ...json,attempted_at:"2026-11-12T17:45:00Z",
        snapshot:{...json.snapshot,at:"2026-11-12T17:45:00+00:00"},
      }});
    }
  });
  await page.route("**/api/v1/messages",async route=>{
    const b=route.request().postDataJSON() as {at:string};
    await route.continue({postData:JSON.stringify({...b,at:T2})});
  });
  try {
    const response=await send(page,"Проверка частичного выполнения");
    expect(response.status()).toBe(409);
    const panel=page.locator('[data-action-kind="partial"]');
    await expect(panel).toBeVisible();
    await expect(panel.getByRole("status")).toContainText("не подтверждено");
    await expect(panel.getByRole("button",{name:"Закрыть уведомление"})).toBeDisabled();
    expect(posts).toBe(1);
    await panel.getByRole("button",{name:"Обновить состояние номера"}).click();
    await expect(panel.getByRole("status")).toContainText("Фактическое состояние получено");
    expect(posts).toBe(1);
  } finally {await cleanup(request,token);}
});

test("MR-NEW-02: 320x568 unresolved partial, nonempty draft disables send until safe GET",
  async ({page,request,browserName}) => {
  await page.setViewportSize({width:320,height:568});
  const token=await connect(page,request);
  let posts=0;
  page.on("request",r=>{if(r.url().endsWith("/api/v1/messages") && r.method()==="POST")posts++;});
  await page.route("**/api/v1/messages",async route=>{
    const b=route.request().postDataJSON() as {at:string};
    await route.continue({postData:JSON.stringify({...b,at:T2})});
  });
  try {
    const partial=await send(page,"Проверка частичного выполнения без состояния");
    expect(partial.status()).toBe(409);
    const panel=page.locator('[data-action-kind="partial"]');
    await expect(panel.getByRole("status")).toContainText("не подтверждено");
    const draft=page.getByRole("textbox",{name:"Просьба",exact:true});
    await draft.fill("Сделай потеплее");
    const sendButton=page.getByRole("button",{name:"Отправить просьбу"});
    await expect(sendButton).toBeDisabled();
    await expect(page.locator(".design-composer")).toHaveClass(/recovery-blocked/);
    await expect(sendButton).toHaveAttribute("aria-describedby","sain-action-hint");
    expect(posts).toBe(1);
    mkdirSync("evidence",{recursive:true});
    await page.screenshot({path:`evidence/mrnew02-blocked-${browserName}-320x568.png`,fullPage:true});
    await panel.getByRole("button",{name:"Обновить состояние номера"}).click();
    await expect(panel.getByRole("status")).toContainText("Фактическое состояние получено");
    await expect(draft).toHaveValue("Сделай потеплее");
    await expect(sendButton).toBeEnabled();
    expect(posts).toBe(1);
  } finally {await cleanup(request,token);}
});

for(const [width,height] of [[320,568],[360,640],[375,667],[375,812],[390,844],[430,932],[768,1024],[1440,900]] as const){
  test(`MR-NEW-03 in-flow notice and 6 devices at ${width}x${height}`,async ({page,request,browserName})=>{
    await page.setViewportSize({width,height});
    const token=await connect(page,request);
    try {
      const partial=await send(page,"Проверка частичного выполнения");
      expect(partial.status()).toBe(409);
      const panel=page.locator('[data-action-kind="partial"]');
      await expect(panel).toBeVisible();
      await expect(panel.getByRole("status")).toContainText("Фактическое состояние получено");
      const dimensions=await panel.evaluate(e=>({width:e.getBoundingClientRect().width,
        position:getComputedStyle(e).position,overflowX:document.documentElement.scrollWidth}));
      expect(dimensions.width).toBeGreaterThan(150);
      expect(dimensions.overflowX).toBeLessThanOrEqual(width+2);
      if(width<=649) expect(dimensions.position).not.toBe("absolute");
      const refresh=panel.getByRole("button",{name:"Обновить состояние номера"});
      await refresh.scrollIntoViewIfNeeded();
      await refresh.focus();
      await expect(refresh).toBeFocused();
      await page.keyboard.press("Enter");
      await expect(panel.getByRole("status")).toContainText("Фактическое состояние получено");
      mkdirSync("evidence",{recursive:true});
      await page.screenshot({path:`evidence/mrnew03-inflow-${browserName}-${width}x${height}.png`,fullPage:true});
      const dismiss=panel.getByRole("button",{name:"Закрыть уведомление"});
      await dismiss.scrollIntoViewIfNeeded();
      await dismiss.click();
      await expect(panel).toHaveCount(0);
      await page.getByRole("button",{name:"Меню"}).click();
      await page.getByRole("navigation").getByRole("button",{name:"Мой номер",exact:true}).click();
      await expect(page.locator(".device").first()).toBeVisible();
      const deviceCount=await page.locator(".device").count();
      expect(deviceCount).toBeGreaterThanOrEqual(6);
    }finally {await cleanup(request,token);}
  });
}

test("MR-NEW-03 200% CSS zoom retains keyboard-reachable recovery controls",
  async ({page,request})=>{
    await page.setViewportSize({width:375,height:667});
    const token=await connect(page,request);
    try {
      const partial=await send(page,"Проверка частичного выполнения");
      expect(partial.status()).toBe(409);
      await page.evaluate(()=>{document.body.style.zoom="2";});
      const panel=page.locator('[data-action-kind="partial"]');
      const refresh=panel.getByRole("button",{name:"Обновить состояние номера"});
      await refresh.scrollIntoViewIfNeeded();
      await refresh.focus();
      await page.keyboard.press("Enter");
      await expect(panel.getByRole("status")).toContainText("Фактическое состояние получено");
    }finally {await cleanup(request,token);}
  });
