import { test, expect } from '@playwright/test';
import type { Page, APIRequestContext } from '@playwright/test';
import { mkdirSync, writeFileSync } from 'node:fs';
const api = 'http://127.0.0.1:8765/api/v1';
const sizes: [number, number][] = [[320,568],[360,800],[375,812],[390,844],[430,932],[768,1024],[1024,768],[1280,800],[1440,900],[1920,1080]];
async function enter(page: Page, request: APIRequestContext) {
  const opened = await request.post(api+'/sessions',{headers:{Authorization:'Bearer offline-team'},data:{source:'dev',stay_id:'stay_test'}});
  expect(opened.status()).toBe(201);
  const data = await opened.json();
  await page.goto('/');
  await page.getByLabel('Временный токен гостя').fill(data.session_token);
  await page.getByRole('button',{name:'Подключиться',exact:true}).click();
  await expect(page.getByRole('button',{name:'Заселиться'})).toBeVisible();
  return data as {session_token:string,at:string};
}
async function go(page: Page, name: string) {
  await page.getByRole('button',{name:'Меню',exact:true}).click();
  await page.getByRole('navigation').getByRole('button',{name,exact:true}).click();
}
const card = (page: Page) => page.locator('button.device').filter({hasText:'Звук'}).first();
const evidence = (name:string) => {
  const root=process.env.SAIN_SCREENSHOTS;
  if (!root) return null;
  mkdirSync(root+'/quality-gate',{recursive:true});
  return root+'/quality-gate/'+name;
};
async function measure(page:Page,title:string){
 return card(page).evaluate((el,expected)=>{
   const labels=Array.from(el.querySelectorAll<HTMLElement>('.design-label,strong'));
   const label=labels.find(e=>e.textContent?.trim()===expected);
   if(!label)return {found:false,expected,rendered:el.textContent,width:innerWidth};
   const r=label.getBoundingClientRect(), box=el.getBoundingClientRect();
   const range=document.createRange();range.selectNodeContents(label);
   const glyphs=Array.from(range.getClientRects());
   const bottom=Math.max(r.bottom,...glyphs.map(x=>x.bottom));
   const meter=el.querySelector('.indicator-meter,.meter');
   const mr=meter?.getBoundingClientRect();
   const barTop=mr?(meter?.classList.contains('indicator-meter')?mr.top+mr.height/2-2:mr.top):undefined;
   const clipped=label.scrollHeight>label.clientHeight+1||label.scrollWidth>label.clientWidth+1||
     glyphs.some(g=>g.left<box.left-2||g.right>box.right+2)||bottom>box.bottom+1;
   return {found:true,expected,width:innerWidth,height:innerHeight,
     clipped,meterOverlap:barTop!==undefined&&bottom>barTop-1,
     horizontalOverflow:document.documentElement.scrollWidth>innerWidth+1,
     fontSize:getComputedStyle(label).fontSize,lineHeight:getComputedStyle(label).lineHeight,
     textBottom:bottom,barTop,lines:glyphs.length};
 },title);
}
test('V06: 12 real catalog tracks × 10 viewports, API confirmation and keyboard',async({page,request})=>{
  test.setTimeout(180000);
  const session=await enter(page,request);
  const headers={Authorization:'Bearer '+session.session_token};
  const response=await request.get(api+'/catalog',{headers});expect(response.status()).toBe(200);
  const tracks=(await response.json()).tracks as {track_id:string,title:string}[];
  expect(tracks).toHaveLength(12);
  await go(page,'Мой номер');await card(page).click();
  await page.getByRole('slider',{name:'Громкость'}).fill('48');
  await page.getByRole('button',{name:/^Сохранить/}).click();
  await expect(page.locator('.reply.done')).toBeVisible();
  const metrics:object[]=[];
  for (const [index,t] of tracks.entries()){
    await page.setViewportSize({width:375,height:812});
    await go(page,'Мой номер');await card(page).click();
    const pick=page.getByLabel('Трек',{exact:true});
    await pick.selectOption(t.track_id);
    await expect(pick.locator('option:checked')).toHaveText(t.title);
    const response=page.waitForResponse(r=>r.url().endsWith('/devices')&&r.request().method()==='POST');
    await page.getByRole('button',{name:/^Сохранить/}).click();
    const answer=await response; expect(answer.status()).toBe(200);
    const confirmed=await answer.json();
    expect(confirmed.reply.response_class).toBe('done');
    expect(confirmed.state.sound.track_id).toBe(t.track_id);
    expect(Number(confirmed.state.sound.volume)).toBeGreaterThan(0);
    await go(page,'Диалог'); await go(page,'Мой номер');
    for(const [width,height] of sizes){
      await page.setViewportSize({width,height});
      await expect(card(page)).toContainText(t.title);
      const result=await measure(page,t.title);
      metrics.push({track_id:t.track_id,...result});
      expect(result,t.track_id+' '+width+' missing').toHaveProperty('found',true);
      expect(result,t.track_id+' '+width+' clipped').toHaveProperty('clipped',false);
      expect(result,t.track_id+' '+width+' overlap').toHaveProperty('meterOverlap',false);
      expect(result,t.track_id+' '+width+' page overflow').toHaveProperty('horizontalOverflow',false);
      const file=evidence('track-'+t.track_id+'-'+width+'.png');
      if(file&&(width===375||(index===6&&[320,1440,1920].includes(width))))
        await page.screenshot({path:file,animations:'disabled'});
    }
    await page.setViewportSize({width:375,height:812});
    await card(page).focus(); await expect(card(page)).toBeFocused();
    await page.keyboard.press('Enter');
    await expect(page.getByLabel('Трек',{exact:true}).locator('option:checked')).toHaveText(t.title);
    await page.getByRole('button',{name:'Назад'}).click();
  }
  const metricsFile=evidence('tracks-120-measurements.json');
  if(metricsFile)writeFileSync(metricsFile,JSON.stringify({sha:process.env.GITHUB_SHA||'local',metrics},null,2));
  expect(metrics).toHaveLength(120);
});
