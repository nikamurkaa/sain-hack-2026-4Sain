import { expect, test } from '@playwright/test';
import type { Page, APIRequestContext } from '@playwright/test';
import { mkdirSync, writeFileSync } from 'node:fs';
const api='http://127.0.0.1:8765/api/v1';
const shotFile=(name:string)=>{const r=process.env.SAIN_SCREENSHOTS;if(!r)return null;
  mkdirSync(r+'/quality-gate',{recursive:true});return r+'/quality-gate/'+name;};
async function enter(page:Page,request:APIRequestContext,source:'dev'|'final'='dev'){
  const opened=await request.post(api+'/sessions',{headers:{Authorization:'Bearer offline-team'},
    data:source==='final'?{source}:{source,stay_id:'stay_test'}});
  expect(opened.status()).toBe(201);const token=(await opened.json()).session_token;
  await page.goto('/');await page.getByLabel('Временный токен гостя').fill(token);
  await page.getByRole('button',{name:'Подключиться',exact:true}).click();
  await expect(page.getByRole('button',{name:'Заселиться'})).toBeVisible();
  return token;
}
async function go(page:Page,name:string){await page.getByRole('button',{name:'Меню'}).click();
  await page.getByRole('navigation').getByRole('button',{name,exact:true}).click();}
test('V08/V14/V13: important screens at mobile, tablet, desktop and 200% CSS zoom',async({page,request})=>{
  test.setTimeout(120000);await enter(page,request);
  const measures:object[]=[];
  for(const [w,h] of [[375,812],[768,1024],[1024,768],[1440,900],[1920,1080]] as const){
    await page.setViewportSize({width:w,height:h});
    for(const screen of ['Мой номер','Диалог','Виртуальное время','Профиль гостя']){
      await go(page,screen);
      await expect(page.getByRole('button',{name:'Меню'})).toBeVisible();
      const m=await page.evaluate(()=>({width:innerWidth,height:innerHeight,
        docWidth:document.documentElement.scrollWidth,
        overflows:document.documentElement.scrollWidth>innerWidth+1,
        smallTexts:Array.from(document.querySelectorAll<HTMLElement>('.design-label,.mode-caption,.device small,.timeline small'))
          .filter(e=>e.offsetWidth>0&&e.offsetHeight>0)
          .filter(e=>parseFloat(getComputedStyle(e).fontSize)<11)
          .slice(0,15).map(e=>({text:(e.textContent||'').trim().slice(0,50),size:getComputedStyle(e).fontSize}))}));
      measures.push({screen, ...m});
      const file=shotFile('screen-'+screen.replaceAll(' ','_')+'-'+w+'.png');
      if(file)await page.screenshot({path:file,animations:'disabled'});
    }
  }
  await page.setViewportSize({width:375,height:812});
  await go(page,'Мой номер');
  await page.evaluate(()=>{document.documentElement.style.zoom='200%';});
  const mZoom=await page.evaluate(()=>({cssZoom:getComputedStyle(document.documentElement).zoom,
    scrollWidth:document.documentElement.scrollWidth,viewportWidth:innerWidth}));
  measures.push({screen:'room 200% CSS zoom',...mZoom});
  const mobile=shotFile('zoom-200-mobile.png');if(mobile)await page.screenshot({path:mobile,animations:'disabled'});
  await page.evaluate(()=>{document.documentElement.style.zoom='';});
  await page.setViewportSize({width:1440,height:900});
  await page.evaluate(()=>{document.documentElement.style.zoom='200%';});
  const desktop=shotFile('zoom-200-desktop.png');if(desktop)await page.screenshot({path:desktop,animations:'disabled'});
  await page.evaluate(()=>{document.documentElement.style.zoom='';});
  await page.emulateMedia({reducedMotion:'reduce'});
  measures.push({screen:'reduced motion',media:await page.evaluate(()=>matchMedia('(prefers-reduced-motion: reduce)').matches)});
  await page.getByRole('button',{name:'Меню'}).focus();
  await expect(page.getByRole('button',{name:'Меню'})).toBeFocused();
  await page.keyboard.press('Enter');await expect(page.getByRole('navigation')).toBeVisible();
  await page.keyboard.press('Escape');await expect(page.getByRole('navigation')).toHaveCount(0);
  const out=shotFile('a11y-zoom-responsive-metrics.json');if(out)writeFileSync(out,JSON.stringify(measures,null,2));
  expect(measures).toHaveLength(22);
});
test('V04/C07: final read-only marker and keyboard route remain explicit',async({page,request})=>{
  await enter(page,request,'final');
  await expect(page.getByText('Финальный гость · просмотр')).toBeVisible();
  await go(page,'Мой номер');
  await expect(page.getByText('Финальный гость · просмотр')).toBeVisible();
  await expect(page.getByRole('textbox',{name:'Просьба'})).toHaveCount(0);
  const file=shotFile('final-readonly-375.png');if(file)await page.screenshot({path:file,animations:'disabled'});
  await go(page,'Диалог');
  await expect(page.getByLabel('Голосовой ввод')).toHaveCount(0);
});
