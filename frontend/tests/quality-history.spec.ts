import { test, expect } from '@playwright/test';
import { mkdirSync, writeFileSync } from 'node:fs';
const api = 'http://127.0.0.1:8765/api/v1';
const save = (name:string) => { const root=process.env.SAIN_SCREENSHOTS; if(!root)return null;
  mkdirSync(root+'/quality-gate',{recursive:true}); return root+'/quality-gate/'+name; };
const go = async(page:import('@playwright/test').Page,name:string)=>{
  await page.getByRole('button',{name:'Меню',exact:true}).click();
  await page.getByRole('navigation').getByRole('button',{name,exact:true}).click();
};
test('V02/V07/UX-02: 100 real messages, long history, scroll, re-entry and desktop',async({page,request})=>{
  test.setTimeout(180000);
  const opened=await request.post(api+'/sessions',{headers:{Authorization:'Bearer offline-team'},
    data:{source:'dev',stay_id:'stay_test'}});
  expect(opened.status()).toBe(201);
  const session=await opened.json(), headers={Authorization:'Bearer '+session.session_token};
  const phrase='Длинный текст для проверки переноса строки и содержимого истории. '.repeat(7);
  for(let i=0;i<100;i++){
    const response=await request.post(api+'/messages',{headers:{...headers,'Idempotency-Key':'long-history-'+String(i).padStart(4,'0')},
      data:{at:session.at,text:'Проверка сообщения '+String(i+1).padStart(3,'0')+'. '+phrase}});
    expect(response.status(),'message '+i).toBe(200);
  }
  const actual=await request.get(api+'/session',{headers});
  expect(actual.status()).toBe(200);
  const history=(await actual.json()).history;
  expect(history).toHaveLength(100);
  await page.goto('/');
  await page.getByLabel('Временный токен гостя').fill(session.session_token);
  await page.getByRole('button',{name:'Подключиться',exact:true}).click();
  await go(page,'Диалог');
  await page.getByRole('button',{name:'Диалог · История сообщений'}).click();
  const dialog=page.getByRole('dialog',{name:'История диалога'});
  await expect(dialog).toBeVisible();
  await expect(dialog.locator('.exchange')).toHaveCount(100);
  await expect(dialog).toContainText('Проверка сообщения 100');
  const log=dialog.locator('[role="log"]');
  const metrics=await log.evaluate(el=>{el.scrollTop=el.scrollHeight;
    return {scrollHeight:el.scrollHeight,clientHeight:el.clientHeight,scrollTop:el.scrollTop};});
  expect(metrics.scrollHeight).toBeGreaterThan(metrics.clientHeight);
  await expect(dialog.locator('.exchange').last()).toBeInViewport();
  const shot=save('long-history-100-mobile.png');if(shot)await page.screenshot({path:shot,animations:'disabled'});
  await page.keyboard.press('Escape');await expect(dialog).not.toBeVisible();
  await page.setViewportSize({width:1440,height:900});
  await go(page,'Диалог');
  await expect(page.locator('.log .exchange')).toHaveCount(100);
  const desktop=save('long-history-100-desktop.png');if(desktop)await page.screenshot({path:desktop,animations:'disabled'});
  const meta=save('long-history-100.json');if(meta)writeFileSync(meta,JSON.stringify({count:100,metrics}));
  await page.reload();
  await expect(page.getByLabel('Временный токен гостя')).toBeVisible();
  await page.getByLabel('Временный токен гостя').fill(session.session_token);
  await page.getByRole('button',{name:'Подключиться',exact:true}).click();
  await go(page,'Диалог');await expect(page.locator('.log .exchange')).toHaveCount(100);
});

test('UX-02: delayed response, duplicate Enter, screen switching, network error and Escape',async({page,request})=>{
  test.setTimeout(90000);
  const opened=await request.post(api+'/sessions',{headers:{Authorization:'Bearer offline-team'},data:{source:'dev',stay_id:'stay_test'}});
  expect(opened.status()).toBe(201);const token=(await opened.json()).session_token;
  await page.goto('/');await page.getByLabel('Временный токен гостя').fill(token);
  await page.getByRole('button',{name:'Подключиться',exact:true}).click();await go(page,'Диалог');
  const input=page.getByRole('textbox',{name:'Просьба'});await input.fill('Сделай попрохладнее');
  let release!:()=>void;const delayed=new Promise<void>(resolve=>{release=resolve;});let calls=0;
  await page.route('**/api/v1/messages',async route=>{calls++;await delayed;await route.abort();});
  await input.press('Enter');
  await expect(input).toBeDisabled();
  await input.press('Enter',{noWaitAfter:true,timeout:500}).catch(()=>{});
  release();await expect(page.getByRole('alert')).toBeVisible();expect(calls).toBe(1);
  await page.unroute('**/api/v1/messages');
  await go(page,'Мой номер');await go(page,'Диалог');await expect(page.getByRole('alert')).toBeVisible();
  await page.getByRole('button',{name:'Меню'}).click();
  await page.keyboard.press('Escape');await expect(page.getByRole('navigation')).toHaveCount(0);
  const shot=save('network-error-mobile.png');if(shot)await page.screenshot({path:shot,animations:'disabled'});
});
