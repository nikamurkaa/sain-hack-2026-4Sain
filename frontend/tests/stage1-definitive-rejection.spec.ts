import { test, expect } from "@playwright/test";
import { mkdirSync } from "node:fs";
import type { Page, APIRequestContext } from "@playwright/test";

const host="http://127.0.0.1:8765";

async function connect(page:Page,request:APIRequestContext) {
  const opened=await request.post(host+"/api/v1/sessions",{
    headers:{Authorization:"Bearer offline-team"},
    data:{source:"dev",stay_id:"stay_test"},
  });
  expect(opened.status()).toBe(201);
  const token=(await opened.json()).session_token as string;
  await page.goto("/");
  await page.getByLabel("Временный токен гостя").fill(token);
  await page.getByRole("button",{name:"Подключиться",exact:true}).click();
  await expect(page.getByRole("button",{name:"Заселиться"})).toBeVisible();
  await page.getByRole("button",{name:"Меню"}).click();
  await page.getByRole("navigation").getByRole("button",{name:"Диалог",exact:true}).click();
  return token;
}

for (const [width,height] of [[320,568],[375,812],[1440,900]] as const) {
  test(`MR-NEW-06 RED: real FastAPI pre-handler 422 allows edited explicit new-key send ${width}x${height}`,
  async ({page,request,browserName})=>{
    await page.setViewportSize({width,height});
    const token=await connect(page,request);
    const auth={Authorization:"Bearer "+token};
    let wirePosts=0;const keys:string[]=[];
    let mutated=false;
    await page.route("**/api/v1/messages",async route=>{
      wirePosts++;
      keys.push((await route.request().allHeaders())["idempotency-key"]);
      if(!mutated){
        mutated=true;
        const body=route.request().postDataJSON() as {at:string;text:string};
        await route.continue({postData:JSON.stringify({...body,text:""})});
      } else await route.continue();
    });
    try {
      const first=await request.get(host+"/api/v1/state",{headers:auth});
      expect(first.status()).toBe(200);
      const firstState=(await first.json()).state;
      const draft=page.getByRole("textbox",{name:"Просьба",exact:true});
      const button=page.getByRole("button",{name:"Отправить просьбу"});
      await draft.fill("Сделай попрохладнее");
      const rejected=page.waitForResponse(r=>r.url().endsWith("/api/v1/messages") && r.status()===422);
      await button.click();
      const errorResponse=await rejected;
      const rejection=await errorResponse.json();
      expect(rejection.detail?.[0]?.type).toBe("string_too_short");
      const session=await request.get(host+"/api/v1/session",{headers:auth});
      const info=await session.json();
      expect(info.reconciliation_required).toBe(false);
      expect(info.pending_action).toBeNull();
      expect(info.history).toHaveLength(0);
      const after=await request.get(host+"/api/v1/state",{headers:auth});
      expect((await after.json()).state).toEqual(firstState);
      expect(wirePosts).toBe(1);
      await expect(page.getByRole("alert")).toContainText("Проверьте");
      await expect(draft).toHaveValue("Сделай попрохладнее");
      await draft.fill("Сделай потеплее");
      await expect(button).toBeEnabled();
      await expect(page.getByRole("button",{name:"Повторить",exact:true})).toHaveCount(0);
      expect(wirePosts).toBe(1);
      mkdirSync("evidence",{recursive:true});
      await page.screenshot({path:`evidence/mrnew06-rejected-${browserName}-${width}x${height}.png`,fullPage:true});
      const accepted=page.waitForResponse(r=>r.url().endsWith("/api/v1/messages") && r.status()===200);
      await button.click();
      const result=await accepted;
      expect((await result.json()).reply.response_class).toBe("done");
      expect(wirePosts).toBe(2);
      expect(keys[0]).toBeTruthy();
      expect(keys[1]).not.toBe(keys[0]);
      const final=await request.get(host+"/api/v1/session",{headers:auth});
      expect((await final.json()).history.length).toBe(1);
      const state=await request.get(host+"/api/v1/state",{headers:auth});
      expect((await state.json()).state).not.toEqual(firstState);
    }finally{
      await request.delete(host+"/api/v1/session",{headers:auth});
    }
  });
}


test("MR-NEW-06: manual device Pydantic 422 does not strand the UI or reuse the key",async ({page,request})=>{
  await page.setViewportSize({width:1440,height:900});
  const token=await connect(page,request);
  const auth={Authorization:"Bearer "+token};
  const before=(await (await request.get(host+"/api/v1/state",{headers:auth})).json()).state;
  const keys:string[]=[];
  let first=true;
  await page.route("**/api/v1/devices",async route=>{
    keys.push((await route.request().allHeaders())["idempotency-key"]);
    if(first){
      first=false;
      const body=route.request().postDataJSON() as {at:string;device_id:string;values:unknown};
      await route.continue({postData:JSON.stringify({...body,values:{}})});
    } else await route.continue();
  });
  async function openClimate(){
    await page.getByRole("button",{name:"Меню"}).click();
    await page.getByRole("navigation").getByRole("button",{name:"Мой номер",exact:true}).click();
    await page.locator(".device").filter({hasText:"Климат"}).first().click();
    await expect(page.getByRole("heading",{name:"Климат",exact:true})).toBeVisible();
    await page.locator(".settings input[type=number]").fill("23");
  }
  try {
    await openClimate();
    const rejected=page.waitForResponse(r=>r.url().endsWith("/api/v1/devices")&&r.status()===422);
    await page.getByRole("button",{name:"Сохранить"}).click();
    const bad=await rejected;
    expect(bad.headers()["x-sain-rejection-class"]).toBe("prehandler");
    const info=(await (await request.get(host+"/api/v1/session",{headers:auth})).json());
    expect(info.pending_action).toBeNull();
    expect(info.reconciliation_required).toBe(false);
    expect(info.history).toHaveLength(0);
    expect((await (await request.get(host+"/api/v1/state",{headers:auth})).json()).state).toEqual(before);
    await expect(page.getByRole("alert")).toContainText("Проверьте");
    await page.getByRole("textbox",{name:"Просьба",exact:true}).fill("Сделай потеплее");
    await expect(page.getByRole("button",{name:"Отправить просьбу"})).toBeEnabled();
    expect(keys).toHaveLength(1);
    await openClimate();
    const accepted=page.waitForResponse(r=>r.url().endsWith("/api/v1/devices")&&r.status()===200);
    await page.getByRole("button",{name:"Сохранить"}).click();
    expect((await (await accepted).json()).reply.response_class).toBe("done");
    expect(keys).toHaveLength(2);
    expect(keys[0]).not.toBe(keys[1]);
    const state=(await (await request.get(host+"/api/v1/state",{headers:auth})).json()).state;
    expect(state.climate.temperature_c).toBe(23);
  }finally{
    await request.delete(host+"/api/v1/session",{headers:auth});
  }
});
