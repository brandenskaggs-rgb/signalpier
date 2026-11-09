const {chromium}=require('playwright'),assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch(process.env.BROWSER_CHANNEL?{channel:process.env.BROWSER_CHANNEL,headless:true}:{headless:true});
 try{
  const page=await browser.newPage(),errors=[];let online=true,newer=true,installs=0;
  page.on('pageerror',e=>errors.push(e.message));
  await page.route('**/api/update**',route=>{
   if(route.request().url().endsWith('/install')){installs++;return route.fulfill({json:{ok:true}});}
   return route.fulfill({json:{current:'0.1.0-alpha.4',latest:newer?'0.1.0-alpha.5':'0.1.0-alpha.4',available:online&&newer,online,installer:{supported:true,status:'idle'}}});
  });
  await page.goto(process.env.APP_URL||'http://127.0.0.1:8766');
  await page.waitForFunction(()=>document.getElementById('update-dialog').open);
  assert.equal(installs,0);assert.match(await page.locator('#update-dialog-message').innerText(),/alpha.5/);
  await page.locator('#update-dialog-later').click();assert.equal(await page.locator('#update-dialog').evaluate(e=>e.open),false);assert.equal(installs,0);
  await page.locator('[data-panel=projects]').click();await page.locator('#check-updates').click();
  await page.waitForFunction(()=>document.getElementById('update-dialog').open);
  await page.locator('#update-dialog-later').click();
  online=false;await page.locator('#check-updates').click();
  await page.waitForFunction(()=>document.getElementById('update-check-status').textContent.includes('offline'));
  assert.equal(await page.locator('#update-dialog').evaluate(e=>e.open),false);
  online=true;newer=false;await page.locator('#check-updates').click();
  await page.waitForFunction(()=>document.getElementById('update-check-status').textContent.includes('up to date'));
  assert.equal(await page.locator('#update-dialog').evaluate(e=>e.open),false);
  newer=true;await page.locator('#check-updates').click();await page.waitForFunction(()=>document.getElementById('update-dialog').open);
  await page.locator('#update-dialog-install').click();await page.waitForTimeout(200);assert.equal(installs,1);assert.deepEqual(errors,[]);
  console.log('Update popup: newer/same/offline, Later, manual recheck and explicit Install passed.');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
