const {chromium}=require('playwright'),assert=require('node:assert/strict');
(async()=>{
  const browser=await chromium.launch(process.env.BROWSER_CHANNEL?{channel:process.env.BROWSER_CHANNEL,headless:true}:{headless:true});
  try{
    const page=await browser.newPage(),errors=[];let installed=false,quit=false;
    page.on('pageerror',e=>errors.push(e.message));
    await page.route('**/api/status*',async route=>{const response=await route.fetch();const data=await response.json();await route.fulfill({json:{...data,portable:true}});});
    await page.route('**/api/update',route=>route.fulfill({json:{current:'0.1.0-alpha.2',latest:'0.1.0-alpha.3',available:true,online:true,installer:{supported:true,status:installed?'complete':'idle',restart_required:installed,message:installed?'Update installed. Quit and reopen SignalPier.':''}}}));
    await page.route('**/api/update/install',route=>{installed=true;return route.fulfill({json:{ok:true}});});
    await page.route('**/api/quit',route=>{quit=true;return route.fulfill({json:{ok:true}});});
    await page.goto('http://127.0.0.1:8766');
    await page.waitForFunction(()=>!document.getElementById('quit-app').hidden);
    assert.equal(installed,false);
    await page.locator('#install-update').click();
    await page.waitForFunction(()=>document.getElementById('update-title').textContent==='Update installed');
    assert.equal(installed,true);
    assert.equal(await page.locator('#install-update').isDisabled(),true);
    await page.locator('#quit-app').click();
    assert.equal(quit,true);await page.waitForTimeout(1800);
    assert.match(await page.locator('body').innerText(),/SignalPier is closed/);assert.deepEqual(errors,[]);
    console.log('AppImage update notice, click-to-install, reopen instruction and Quit UI passed.');
  }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
