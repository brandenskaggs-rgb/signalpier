const {chromium}=require('playwright'),assert=require('node:assert/strict');
(async()=>{
  const browser=await chromium.launch(process.env.BROWSER_CHANNEL?{channel:process.env.BROWSER_CHANNEL,headless:true}:{headless:true});
  try{
    const page=await browser.newPage({viewport:{width:390,height:844}}),errors=[];let connected=false,ready=false,starts=0,probes=0;
    page.on('pageerror',e=>errors.push(e.message));
    await page.route('**/api/receivers**',route=>{
      if(route.request().method()==='POST'){
        probes++;assert.equal(route.request().postDataJSON().device,'1');
        return route.fulfill({json:{status:ready?'ready':'permission_denied',message:ready?'Connection test passed.':'USB access was denied. Enable USB receiver access in Settings.',checked_at:Date.now()/1000}});
      }
      return route.fulfill({json:{status:connected?'detected':'not_connected',message:connected?'Receiver detected.':'No supported RTL-SDR found.',active:false,devices:connected?[{index:1,name:'RTL-SDR',product:'Blog V3 <receiver>',serial:'00000002'}]:[]}});
    });
    await page.route('**/api/start',route=>{starts++;return route.fulfill({json:{ok:true}});});
    await page.goto('http://127.0.0.1:8766');
    await page.waitForFunction(()=>document.getElementById('receiver-message').textContent.includes('No supported'));
    assert.equal(await page.locator('#test-receiver').isDisabled(),true);
    connected=true;await page.locator('#refresh-receivers').click();
    await page.waitForFunction(()=>!document.getElementById('test-receiver').disabled);
    assert.equal(await page.locator('#device').inputValue(),'1');
    assert.equal(await page.locator('#mode').inputValue(),'demo');
    await page.locator('#test-receiver').click();
    await page.waitForFunction(()=>document.getElementById('receiver-test-result').textContent.includes('denied'));
    ready=true;await page.locator('#test-receiver').click();
    await page.waitForFunction(()=>document.getElementById('receiver-test-result').textContent.includes('passed'));
    connected=false;await page.locator('#refresh-receivers').click();
    await page.waitForFunction(()=>document.getElementById('test-receiver').disabled);
    assert.equal(starts,0);assert.equal(probes,2);
    assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));assert.deepEqual(errors,[]);
    console.log('Receiver discovery, selection, permission/ready results, unplug handling and mobile layout passed.');
  }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
