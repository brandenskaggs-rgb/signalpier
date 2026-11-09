'use strict';
const $ = id => document.getElementById(id);
let token = '', state = null, lastSignature = '', activePanel = 'receiver', firstRefresh = true, appClosed = false;
let testingReceiver=false, receiverTimer=null, receiverInventory=[];
function sourceLabel() {
  $('source').textContent = activePanel === 'receiver' ? (state?.mode === 'hardware' ? 'HARDWARE · RECEIVED DATA' : 'DEMO · SYNTHETIC DATA') : ({hamclock:'CLOCK · CALCULATED + NOAA',encryption:'LOCAL · AES-256-GCM',projects:'STATION SETTINGS'}[activePanel]);
}
const palette = {bg:'#142b40', grid:'#30495e', muted:'#a9bdcb', trace:'#77d4e2', hot:'#e8b960'};

document.querySelectorAll('.tab').forEach(button => button.addEventListener('click', () => {
  activePanel = button.dataset.panel; sourceLabel();
  document.querySelectorAll('.tab').forEach(tab => { const active = tab === button; tab.classList.toggle('active', active); tab.setAttribute('aria-selected', String(active)); });
  document.querySelectorAll('.panel').forEach(panel => { panel.hidden = panel.id !== button.dataset.panel; });
  if (button.dataset.panel === 'receiver') draw();
}));
$('kind').addEventListener('change', () => {
  const scan = $('kind').value === 'scan';
  $('scan-fields').hidden = !scan;
  $('decode-fields').hidden = scan;
});
function notice(text, error = false) { $('message').textContent = text; $('message').classList.toggle('error', error); }
async function api(path, data) {
  const options = data === undefined ? {} : {method:'POST', headers:{'Content-Type':'application/json','X-Workbench-Token':token}, body:JSON.stringify(data)};
  const response = await fetch(path, options);
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || 'Request failed.');
  return result;
}
$('capture-form').addEventListener('submit', async event => {
  event.preventDefault();
  const data = Object.fromEntries(['mode','kind','start_mhz','end_mhz','bin_khz','frequency_mhz','duration','device'].map(key => [key,$(key).value]));
  $('start').disabled = true;
  try { await api('/api/start', data); await refresh(); }
  catch(error) { notice(error.message,true); $('start').disabled = false; }
});
$('stop').addEventListener('click', async () => {
  try { await api('/api/stop', {}); notice('Stopping the receiver…'); } catch(error) { notice(error.message,true); }
});
function download(name, data) {
  const url = URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:'application/json'}));
  const link = document.createElement('a'); link.href=url; link.download=name; link.click();
  setTimeout(() => URL.revokeObjectURL(url),1000);
}
$('export').addEventListener('click', async () => {
  try { download(`radio-${state.mode}-${state.kind}-${Date.now()}.json`,await api('/api/export')); }
  catch(error) { notice(error.message,true); }
});
function node(tag, text) { const element = document.createElement(tag); element.textContent=text; return element; }
function renderResults() {
  const container = $('results'); container.replaceChildren();
  if (state.kind === 'decode') {
    $('results-title').textContent = 'Decoded packets';
    $('results-help').textContent = 'Supported protocol packets from this capture. No packets may mean silence, weak reception, or an unsupported protocol.';
    for (const packet of [...state.events].reverse()) {
      const item = node('article',''); item.className='event';
      item.append(node('h3', String(packet.model || 'Decoded event')), node('pre',JSON.stringify(packet,null,2))); container.append(item);
    }
    if (!state.events.length) container.append(node('p','No packets in this capture yet.'));
    return;
  }
  $('results-title').textContent = 'Signal candidates';
  $('results-help').textContent = 'Peaks at least 10 dB above the median estimate, from the latest sweep. These are not protocol identifications.';
  if (!state.peaks.length) { const p=node('p','No signal candidates yet. Run a capture or try a different band.'); p.className='empty'; container.append(p); return; }
  const table = node('table',''), head=node('thead',''), row=node('tr','');
  ['FREQUENCY / MHz','RELATIVE / dB','ABOVE MEDIAN / dB'].forEach(label => row.append(node('th',label)));
  head.append(row); table.append(head); const body=node('tbody','');
  for (const peak of state.peaks) { const tr=node('tr',''); [ (peak.frequency_hz/1e6).toFixed(5), peak.power_db.toFixed(1), '+'+peak.above_median_db.toFixed(1)].forEach(value => tr.append(node('td',value))); body.append(tr); }
  table.append(body);container.append(table);
}
function heat(value) {
  if (value === null) return palette.bg;
  const t = Math.max(0, Math.min(1,(value + 85)/55));
  const stops = [[20,43,64],[38,95,131],[119,212,226],[232,185,96]];
  const index = Math.min(2,Math.floor(t*3)), f=t*3-index;
  return `rgb(${stops[index].map((channel,i) => Math.round(channel*(1-f)+stops[index+1][i]*f)).join(',')})`;
}
function draw() {
  const canvas=$('spectrum'), ctx=canvas.getContext('2d'), w=canvas.width,h=canvas.height;
  ctx.fillStyle=palette.bg;ctx.fillRect(0,0,w,h);ctx.font='12px Consolas,monospace';
  const config=state?.config || {start_mhz:430,end_mhz:440};
  const lo=config.start_mhz*1e6, hi=config.end_mhz*1e6;
  const x=f=>48+(f-lo)/(hi-lo)*(w-64), y=p=>Math.max(8,Math.min(h-30,(0-p)/100*(h-40)+8));
  ctx.strokeStyle=palette.grid;ctx.fillStyle=palette.muted;ctx.lineWidth=1;
  for(let db=-20;db>=-80;db-=20){ctx.beginPath();ctx.moveTo(42,y(db));ctx.lineTo(w-12,y(db));ctx.stroke();ctx.fillText(String(db),8,y(db)+4);}
  for(let i=0;i<=5;i++){const px=48+i*(w-64)/5;ctx.beginPath();ctx.moveTo(px,8);ctx.lineTo(px,h-30);ctx.stroke();ctx.fillText(((lo+(hi-lo)*i/5)/1e6).toFixed(2),Math.min(w-55,px-12),h-8);}
  const points=state?.sweeps?.at(-1)?.points || [];
  ctx.strokeStyle=palette.trace;ctx.lineWidth=2;ctx.beginPath();let connected=false;
  for(const [freq,power] of points){if(power===null || freq<lo || freq>hi){connected=false;continue;}if(connected)ctx.lineTo(x(freq),y(power));else ctx.moveTo(x(freq),y(power));connected=true;}ctx.stroke();
  if(!points.length){ctx.fillStyle=palette.muted;ctx.font='15px Consolas,monospace';ctx.fillText(state?.kind==='decode'?'PACKET MODE · SEE DECODED EVENTS BELOW':'AWAITING A SPECTRUM CAPTURE',w/2-180,h/2);}
  const waterfall=$('waterfall'), water=waterfall.getContext('2d');water.fillStyle=palette.bg;water.fillRect(0,0,waterfall.width,waterfall.height);
  const sweeps=state?.sweeps||[], rowHeight=waterfall.height/Math.max(10,sweeps.length);
  for(let row=0;row<sweeps.length;row++){
    const bins=sweeps[row].points;
    for(let i=0;i<bins.length;i++){
      const [freq,power]=bins[i], next=bins[i+1]?.[0] || freq+(bins[i-1]?freq-bins[i-1][0]:1);
      const start=Math.max(0,(freq-lo)/(hi-lo)*waterfall.width),end=Math.min(waterfall.width,(next-lo)/(hi-lo)*waterfall.width);
      if(end<=start)continue;water.fillStyle=heat(power);water.fillRect(start,row*rowHeight,Math.max(1,end-start),Math.ceil(rowHeight));
    }
  }
}
$('spectrum').addEventListener('pointermove',event=>{
  const points=state?.sweeps?.at(-1)?.points;if(!points?.length)return;
  const rect=$('spectrum').getBoundingClientRect(),pixel=(event.clientX-rect.left)/rect.width*1000;
  const config=state.config, freq=(config.start_mhz+(pixel-48)/936*(config.end_mhz-config.start_mhz))*1e6;
  const point=points.reduce((best,item)=>Math.abs(item[0]-freq)<Math.abs(best[0]-freq)?item:best);
  $('cursor').textContent=`${(point[0]/1e6).toFixed(5)} MHz · ${point[1]===null?'gap':point[1].toFixed(1)+' dB'}`;
});
async function refresh() {
  try {
    const update=await api('/api/status'+(state ? '?revision='+state.revision : ''));
    if(appClosed)return;
    state=update.unchanged ? {...state,...update} : update;token=state.token;
    if(firstRefresh && state.config){for(const [key,value] of Object.entries(state.config)){if($(key))$(key).value=value;}$('kind').dispatchEvent(new Event('change'));}firstRefresh=false;
    $('connection').textContent=`Local station · ${state.platform}`;
    $('quit-app').hidden=!state.portable;
    $('usb-setup').hidden=!state.portable;
    sourceLabel();
    $('job-status').textContent=state.status.toUpperCase();
    const running=state.status==='running';$('start').disabled=running||testingReceiver;$('stop').disabled=!running;
    $('test-receiver').disabled=running||testingReceiver||!token||!receiverInventory.length;
    $('detected-receiver').disabled=running||testingReceiver;
    $('export').disabled=!(state.sweeps.length||state.events.length);
    for(const input of $('capture-form').querySelectorAll('input,select'))input.disabled=running;
    const signature=JSON.stringify([state.status,state.mode,state.kind,state.config,state.sweeps.length,state.events.length,state.message]);
    if(signature!==lastSignature){
      lastSignature=signature;notice(state.message,state.status==='error');
      if(state.config){$('band-title').textContent=state.kind==='decode'?`${state.config.frequency_mhz.toFixed(3)} MHz · packets`:`${state.config.start_mhz.toFixed(3)} — ${state.config.end_mhz.toFixed(3)} MHz`;}
      const list=$('tools');list.replaceChildren();
      for(const [name,installed]of Object.entries(state.tools)){const li=node('li',name);li.append(node('span',installed?'available':'not installed'));list.append(li);}
      renderResults();draw();
    }
  } catch(error){if(appClosed)return;$('connection').textContent='Station offline';notice('Cannot reach the local server. Open SignalPier again and refresh.',true);}
}
async function poll(){if(appClosed)return;await refresh();if(!appClosed)setTimeout(poll,1000);}poll();draw();
function cryptoNotice(text){$('crypto-status').textContent=text;}
$('generate').addEventListener('click',()=>{
  if(!globalThis.crypto?.subtle){cryptoNotice('Use http://localhost or an SSH tunnel so browser encryption is available.');return;}
  $('key').value=RadioCrypto.generateKey();$('decrypted').textContent='No message verified yet.';cryptoNotice('New key generated in memory. Save it securely if you need it after closing this page.');
});
$('reveal').addEventListener('click',()=>{const hidden=$('key').type==='password';$('key').type=hidden?'text':'password';$('reveal').textContent=hidden?'Hide key':'Show key';});
$('encrypt').addEventListener('click',async()=>{
  try{$('decrypted').textContent='No message verified yet.';$('envelope').value=JSON.stringify(await RadioCrypto.encrypt($('plaintext').value,$('key').value),null,2);cryptoNotice('Encrypted locally with AES-256-GCM. No radio transmission occurred.');}
  catch(error){cryptoNotice(error.message);}
});
$('decrypt').addEventListener('click',async()=>{
  $('decrypted').textContent='No message verified yet.';
  try{const text=await RadioCrypto.decrypt(JSON.parse($('envelope').value),$('key').value);$('decrypted').textContent=text;cryptoNotice('Authentication verified. The plaintext is shown above.');}
  catch(error){cryptoNotice(error.message);}
});
$('save-envelope').addEventListener('click',()=>{
  try{const envelope=JSON.parse($('envelope').value);if(envelope.version!==1||!envelope.ciphertext)throw new Error('Encrypt a message first.');download('encrypted-message.json',envelope);cryptoNotice('Envelope saved without the secret key.');}
  catch(error){cryptoNotice(error.message);}
});

try{const p=JSON.parse(localStorage.getItem('signalpier-preferences')||'null');if(p&&Number.isInteger(p.device)&&p.device>=0&&p.device<=99&&Number.isInteger(p.duration)&&p.duration>=2&&p.duration<=60){$('default-device').value=p.device;$('default-duration').value=p.duration;$('device').value=p.device;$('duration').value=p.duration;}}catch{}
$('preferences-form').addEventListener('submit',event=>{event.preventDefault();const p={device:Number($('default-device').value),duration:Number($('default-duration').value)};try{localStorage.setItem('signalpier-preferences',JSON.stringify(p));if(state?.status!=='running'){$('device').value=p.device;$('duration').value=p.duration;}$('preferences-message').textContent='Defaults saved for this browser.';}catch{$('preferences-message').textContent='Browser storage is unavailable.';}});

let updateInfo=null, installingUpdate=false, updateTimer=null, dismissedVersion='';
async function checkUpdates(){
  if(appClosed)return;
  try{
    const info=await api('/api/update');updateInfo=info;
    if(appClosed)return;
    const status=info.installer?.status;
    if(status==='complete' && info.installer.restart_required){installingUpdate=false;$('update-notice').hidden=false;$('update-title').textContent='Update installed';$('update-message').textContent=info.installer.message;$('install-update').disabled=true;return;}
    if(installingUpdate && status==='complete'){location.reload();return;}
    if(status==='queued'||status==='installing')installingUpdate=true;
    if(status==='error'){installingUpdate=false;$('update-notice').hidden=false;$('update-title').textContent='Update could not finish';$('update-message').textContent=info.installer.message;$('install-update').disabled=false;}
    else if(installingUpdate){$('update-notice').hidden=false;$('update-title').textContent='Installing SignalPier update';$('update-message').textContent=info.installer.message||'Starting update…';$('install-update').disabled=true;}
    else if(info.available && info.latest!==dismissedVersion){$('update-notice').hidden=false;$('update-title').textContent='SignalPier '+info.latest+' is available';$('update-message').textContent=info.installer?.supported?'Install when ready. Finish any capture first.':'Automatic installation is available with the Pi app installer.';$('install-update').disabled=!info.installer?.supported;}
  }catch{if(installingUpdate)$('update-message').textContent='The app is restarting. Reconnecting…';}
  clearTimeout(updateTimer);updateTimer=setTimeout(checkUpdates,installingUpdate?2500:1800000);
}
$('install-update').addEventListener('click',async()=>{
  $('install-update').disabled=true;
  try{await api('/api/update/install',{});installingUpdate=true;$('update-title').textContent='Installing SignalPier update';$('update-message').textContent='Checking and downloading the update…';clearTimeout(updateTimer);updateTimer=setTimeout(checkUpdates,1500);}
  catch(error){$('update-message').textContent=error.message;$('install-update').disabled=false;}
});
$('dismiss-update').addEventListener('click',()=>{dismissedVersion=updateInfo?.latest||'';$('update-notice').hidden=true;});
window.addEventListener('online',()=>{clearTimeout(updateTimer);updateTimer=setTimeout(checkUpdates,1000);});
checkUpdates();
async function refreshReceivers(force=false){
  if(appClosed||testingReceiver)return;
  $('refresh-receivers').disabled=true;
  try{
    const info=await api('/api/receivers'+(force?'?refresh=1':''));if(appClosed)return;
    if(JSON.stringify(receiverInventory)!==JSON.stringify(info.devices||[]))$('receiver-test-result').textContent='Click Test connection to check the selected receiver.';
    receiverInventory=info.devices||[];
    const select=$('detected-receiver'),previous=select.value||$('device').value;
    select.replaceChildren();
    if(!receiverInventory.length){const option=node('option','No receiver detected');option.value='';select.append(option);}
    for(const device of receiverInventory){const option=node('option',`${device.index} · ${device.product||device.name}${device.serial?' · '+device.serial:''}`);option.value=String(device.index);select.append(option);}
    if(receiverInventory.some(device=>String(device.index)===previous))select.value=previous;
    else if(receiverInventory.length){select.value=String(receiverInventory[0].index);if(state?.status!=='running')$('device').value=select.value;}
    $('receiver-message').textContent=info.active?'Receiver in use by SignalPier. Finish the capture before testing.':info.message;
    document.querySelector('.receiver-connection').dataset.status=info.status;
    if(!receiverInventory.length)$('receiver-test-result').textContent='Demo mode works without a receiver.';
    $('test-receiver').disabled=info.active||testingReceiver||!token||!receiverInventory.length;
  }catch(error){$('receiver-message').textContent='Could not refresh receivers: '+error.message;}
  finally{if(!appClosed){$('refresh-receivers').disabled=false;clearTimeout(receiverTimer);receiverTimer=setTimeout(refreshReceivers,15000);}}
}
$('refresh-receivers').addEventListener('click',()=>{$('receiver-test-result').textContent='Device list checked periodically. A connection test is separate.';refreshReceivers(true);});
$('detected-receiver').addEventListener('change',()=>{if($('detected-receiver').value!=='')$('device').value=$('detected-receiver').value;$('receiver-test-result').textContent='Click Test connection to check this receiver.';});
$('test-receiver').addEventListener('click',async()=>{
  testingReceiver=true;$('test-receiver').disabled=true;$('start').disabled=true;$('receiver-test-result').textContent='Opening the receiver briefly to check access…';
  try{const info=await api('/api/receivers/test',{device:$('detected-receiver').value});$('receiver-test-result').textContent=info.message+' Checked '+new Date(info.checked_at*1000).toLocaleTimeString()+'.';document.querySelector('.receiver-connection').dataset.status=info.status;}
  catch(error){$('receiver-test-result').textContent=error.message;}
  finally{testingReceiver=false;if(!appClosed){await refresh();clearTimeout(receiverTimer);receiverTimer=setTimeout(refreshReceivers,15000);}}
});
refreshReceivers();
$('quit-app').addEventListener('click',async()=>{try{await api('/api/quit',{});appClosed=true;clearTimeout(updateTimer);for(const element of document.body.children)element.hidden=true;document.body.append(node('p','SignalPier is closed. You can close this window.'));}catch(error){notice(error.message,true);}});
$('usb-setup').addEventListener('click',async()=>{const button=$('usb-setup');button.disabled=true;$('usb-status').textContent='Approve the administrator prompt to enable receiver access.';try{await api('/api/usb/setup',{});$('usb-status').textContent='Receiver access enabled. Unplug and reconnect the SDR, then try Hardware mode.';}catch(error){$('usb-status').textContent=error.message;}finally{button.disabled=false;}});
