'use strict';
const repo='https://github.com/brandenskaggs-rgb/signalpier';
document.querySelectorAll('[data-copy]').forEach(button=>button.addEventListener('click',async()=>{try{await navigator.clipboard.writeText(document.getElementById(button.dataset.copy).textContent);button.textContent='Copied';setTimeout(()=>button.textContent='Copy',1800);}catch{button.textContent='Select text to copy';}}));
const scope=document.getElementById('hero-scope');
if(scope){
  const ctx=scope.getContext('2d');let center=433.920;
  function draw(){const w=scope.width,h=scope.height;ctx.fillStyle='#122737';ctx.fillRect(0,0,w,h);ctx.strokeStyle='#29475a';ctx.lineWidth=1;
    for(let x=0;x<w;x+=40){ctx.beginPath();ctx.moveTo(x,0);ctx.lineTo(x,h);ctx.stroke();}for(let y=20;y<h;y+=40){ctx.beginPath();ctx.moveTo(0,y);ctx.lineTo(w,y);ctx.stroke();}
    const values=[];for(let x=0;x<w;x++){const v=10+5*Math.sin(x*1.7)+3*Math.cos(x*.43)+130*Math.exp(-(((x-w*.52)/14)**2))+45*Math.exp(-(((x-w*.23)/30)**2))+72*Math.exp(-(((x-w*.81)/7)**2));values.push(v);}
    ctx.beginPath();ctx.moveTo(0,170);for(let x=0;x<w;x++)ctx.lineTo(x,170-values[x]);ctx.strokeStyle='#9ad9ef';ctx.lineWidth=1.6;ctx.stroke();
    for(let y=185;y<h;y+=3)for(let x=0;x<w;x+=3){const v=values[x]+8*Math.sin(y*.5+x*.1);ctx.fillStyle=v>90?'#ffd168':v>40?'#669fc0':v>19?'#315c79':'#1b394f';ctx.fillRect(x,y,3,3);}
    ctx.strokeStyle='#ffd168';ctx.setLineDash([4,5]);ctx.beginPath();ctx.moveTo(w*.52,0);ctx.lineTo(w*.52,180);ctx.stroke();ctx.setLineDash([]);
    document.getElementById('frequency').innerHTML=center.toFixed(3)+' <small>MHz</small>';
  }
  document.querySelectorAll('[data-band]').forEach(button=>button.addEventListener('click',()=>{center=Number(button.dataset.band);document.querySelectorAll('[data-band]').forEach(item=>item.classList.toggle('selected',item===button));draw();}));draw();
}
async function release(){
  const link=document.getElementById('download-installer');if(!link)return;
  try{const response=await fetch('release.json');if(!response.ok)throw new Error();const data=await response.json();const item=data.appimage;link.href=item.url;document.getElementById('installer-size').textContent=(item.bytes/1048576).toFixed(1)+' MB download';document.getElementById('installer-sha').textContent=item.sha256;document.querySelectorAll('[data-version]').forEach(e=>e.textContent=data.version);document.getElementById('release-date').textContent=data.date;const win=data.windows;if(win){document.getElementById('download-windows').href=win.url;document.getElementById('windows-size').textContent=(win.bytes/1048576).toFixed(1)+' MB download';document.getElementById('windows-sha').textContent=win.sha256;}}
  catch{document.getElementById('release-message').textContent='Alpha app installer. Check GitHub Releases for checksums and validation details.';}
}
release();
