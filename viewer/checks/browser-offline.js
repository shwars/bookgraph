async page=>{
 const checks=[],errors=[];const check=(v,n)=>{if(!v)throw new Error(n);checks.push(n);};
 page.on('pageerror',e=>errors.push(e.message));page.on('console',m=>{if(m.type()==='error')errors.push(m.text());});
 await page.context().setOffline(true);await page.reload();
 await page.locator('#open-reader').click();
 await page.locator('#toc [data-page="source/bespridannica/bychapter/section-09"]').click();
 check((await page.locator('#block-b0002').textContent()).includes('Venez![3]'),'punctuation before note preserved');
 check(await page.locator('#document-body img').count()===0,'footnotes are links, not images');
 await page.locator('#block-b0002 a[data-target]').first().click();
 check(await page.locator('#block-note3.highlight').count()===1,'inline footnote exact target');
 await page.getByRole('button',{name:'Закрыть чтение',exact:true}).click();
 const node=page.locator('#graph [data-id="Гаврило"]');const old=await node.getAttribute('transform');
 const box=await node.locator('circle.portrait-bg').boundingBox();
 await page.mouse.move(box.x+box.width/2,box.y+box.height/2);await page.mouse.down();await page.mouse.move(box.x+box.width/2+45,box.y+box.height/2+25,{steps:8});await page.mouse.up();
 check(await node.getAttribute('transform')!==old,'character drag changes position');
 await page.locator('#graph [data-id="Лариса Огудалова"] circle.portrait-bg').click();
 check(await page.locator('#pin').getAttribute('aria-pressed')==='true','first click pins after drag');
 await page.getByRole('tab',{name:'События: зависимости',exact:true}).click();
 await page.getByRole('searchbox').fill('Гости и Лариса покидают');await page.locator('[data-search-id="Гости и Лариса покидают обед"]').click();
 await page.getByRole('combobox',{name:'Цепочка выбранного события',exact:true}).selectOption('both');
 await page.screenshot({path:'output/playwright/dependencies-chain.png'});
 const remote=await page.evaluate(()=>performance.getEntriesByType('resource').filter(r=>/^https?:/.test(r.name)).map(r=>r.name));
 check(remote.length===0,'zero HTTP resources');check(errors.length===0,'zero page and console errors after fixes');
 await page.getByRole('link',{name:'На главную карту',exact:true}).click();await page.screenshot({path:'output/playwright/final-viewer.png'});
 return {checks,errors,remote};
}

