const {chromium}=require('playwright'),assert=require('node:assert/strict'),fs=require('node:fs');
(async()=>{
  fs.mkdirSync('artifacts',{recursive:true});
  const browser=await chromium.launch(process.env.BROWSER_CHANNEL?{channel:process.env.BROWSER_CHANNEL,headless:true}:{headless:true});
  try{
    const page=await browser.newPage({viewport:{width:1440,height:1000}}),errors=[];
    page.on('pageerror',error=>errors.push(error.message));
    for(const name of ['index','downloads','guide','roadmap']){
      await page.goto(`http://127.0.0.1:8780/${name}.html`);assert.equal(await page.locator('h1').count(),1);
      await page.setViewportSize({width:390,height:844});assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),name+' mobile overflow');await page.setViewportSize({width:1440,height:1000});
    }
    await page.goto('http://127.0.0.1:8780/');await page.screenshot({path:'artifacts/website-desktop.png',fullPage:true});
    assert.match(await page.locator('.hero .primary').getAttribute('href'),/arm64\.deb$/);
    await page.locator('[data-band="145.500"]').click();assert.match(await page.locator('#frequency').innerText(),/145.500/);
    await page.goto('http://127.0.0.1:8766');await page.waitForFunction(()=>document.getElementById('connection').textContent.includes('Local station'));
    await page.locator('#duration').fill('10');await page.locator('#start').click();await page.waitForFunction(()=>document.getElementById('job-status').textContent==='COMPLETE');assert.ok(await page.locator('#results tbody tr').count()>0);
    await page.screenshot({path:'artifacts/dashboard-desktop.png',fullPage:true});
    await page.locator('[data-panel=hamclock]').click();await page.screenshot({path:'artifacts/clock-desktop.png',fullPage:true});
    await page.locator('[data-panel=encryption]').click();await page.locator('#generate').click();await page.locator('#encrypt').click();await page.waitForFunction(()=>document.getElementById('envelope').value.includes('ciphertext'));await page.locator('#decrypt').click();await page.waitForFunction(()=>document.getElementById('decrypted').textContent.includes('Receiver ready'));
    await page.locator('[data-panel=projects]').click();await page.locator('#default-duration').fill('5');await page.locator('#preferences-form button[type=submit]').click();assert.match(await page.locator('#preferences-message').innerText(),/saved/);
    await page.setViewportSize({width:390,height:844});assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));await page.locator('[data-panel=receiver]').click();await page.screenshot({path:'artifacts/dashboard-mobile.png',fullPage:true});assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
    assert.deepEqual(errors,[]);console.log('Website links/layout and app capture, crypto, settings checks passed.');
  }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
