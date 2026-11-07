'use strict';
(() => {
  const byId=id=>document.getElementById(id), solar=RadioSolar;
  let station={callsign:'',home:'',dx:''}, home=null, dx=null, geography=null, lastMinute=-1;
  const utcTime=date=>date.toLocaleTimeString('en-GB',{timeZone:'UTC',hour12:false});
  const utcDate=date=>date.toLocaleDateString('en-GB',{timeZone:'UTC',day:'2-digit',month:'short',year:'numeric'});
  try { const saved=JSON.parse(localStorage.getItem('signalpier-station')||'null');if(saved&&typeof saved==='object')station={callsign:String(saved.callsign||'').slice(0,20),home:String(saved.home||''),dx:String(saved.dx||'')}; } catch {}
  function setStation(){
    home=station.home?solar.fromGrid(station.home):null;dx=station.dx?solar.fromGrid(station.dx):null;
    byId('callsign').value=station.callsign;byId('home-grid').value=station.home;byId('dx-grid').value=station.dx;
    byId('station-title').textContent=station.callsign||'Your station';
    byId('station-position').textContent=home?`${home.grid} · ${home.lat.toFixed(3)}° latitude / ${home.lon.toFixed(3)}° longitude · locator center`:'Set your locator for solar times and a DX bearing.';
    const route=home&&dx?solar.route(home,dx):null;
    byId('dx-distance').textContent=route?`${Math.round(route.distance_km).toLocaleString()} km`:'Set both locators';
    byId('dx-bearing').textContent=route&&route.bearing_deg!==null?`${route.bearing_deg.toFixed(1)}° true`:'—';
    lastMinute=-1;
  }
  try{setStation();}catch{station={callsign:'',home:'',dx:''};setStation();}
  byId('station-form').addEventListener('submit',event=>{
    event.preventDefault();
    try{
      const next={callsign:byId('callsign').value.trim().toUpperCase(),home:byId('home-grid').value.trim().toUpperCase(),dx:byId('dx-grid').value.trim().toUpperCase()};
      if(next.home)solar.fromGrid(next.home);if(next.dx)solar.fromGrid(next.dx);
      station=next;setStation();
      try{localStorage.setItem('signalpier-station',JSON.stringify(station));byId('station-message').textContent='Station saved in this browser. Location stays on this device.';}catch{byId('station-message').textContent='Station set for this session; browser storage is unavailable.';}
      tick();
    }catch(error){byId('station-message').textContent=error.message;}
  });
  function drawWorld(now,sun){
    const canvas=byId('world-map'),ctx=canvas.getContext('2d'),w=canvas.width,h=canvas.height;
    const xy=(lon,lat)=>[(lon+180)/360*w,(90-lat)/180*h];
    ctx.fillStyle='#142b40';ctx.fillRect(0,0,w,h);ctx.strokeStyle='#30495e';ctx.lineWidth=.7;
    for(let lon=-180;lon<=180;lon+=30){const [x]=xy(lon,0);ctx.beginPath();ctx.moveTo(x,0);ctx.lineTo(x,h);ctx.stroke();}
    for(let lat=-60;lat<=60;lat+=30){const [,y]=xy(0,lat);ctx.beginPath();ctx.moveTo(0,y);ctx.lineTo(w,y);ctx.stroke();}
    if(geography){ctx.fillStyle='#63869a';ctx.strokeStyle='#89a7b9';
      for(const feature of geography.features){const geom=feature.geometry,polygons=geom.type==='Polygon'?[geom.coordinates]:geom.type==='MultiPolygon'?geom.coordinates:[];
        for(const polygon of polygons){ctx.beginPath();for(const ring of polygon){ring.forEach(([lon,lat],i)=>{const [x,y]=xy(lon,lat);if(i===0)ctx.moveTo(x,y);else ctx.lineTo(x,y);});ctx.closePath();}ctx.fill('evenodd');ctx.stroke();}
      }
    }else{ctx.fillStyle='#a9bdcb';ctx.font='16px Consolas,monospace';ctx.fillText('Map outline unavailable · solar shading remains active',35,40);}
    // Coarse shading is sufficient for a station clock and keeps browser work light.
    for(let y=0;y<h;y+=5)for(let x=0;x<w;x+=5){const alt=solar.altitude(90-(y+2.5)/h*180,(x+2.5)/w*360-180,sun);if(alt<0){ctx.fillStyle=alt < -18?'rgba(3,12,25,.72)':alt < -6?'rgba(3,12,25,.52)':'rgba(232,185,96,.25)';ctx.fillRect(x,y,5,5);}}
    const mark=(point,label,color)=>{const [x,y]=xy(point.lon,point.lat);ctx.fillStyle=color;ctx.beginPath();ctx.arc(x,y,5,0,Math.PI*2);ctx.fill();ctx.strokeStyle=color;ctx.beginPath();ctx.arc(x,y,10,0,Math.PI*2);ctx.stroke();ctx.font='bold 13px Consolas,monospace';ctx.fillText(label,Math.max(5,Math.min(w-140,x+14)),Math.max(16,y-10));};
    mark(sun,'SUN','#e8b960');if(home)mark(home,station.callsign||'HOME','#77d4e2');if(dx)mark(dx,'DX '+dx.grid,'#fafcfd');
    byId('map-time').textContent=utcTime(now)+' UTC';
  }
  function tick(){
    const now=new Date();byId('utc-clock').textContent=utcTime(now);byId('utc-date').textContent=utcDate(now);
    byId('local-clock').textContent=now.toLocaleTimeString('en-GB',{hour12:false});
    byId('local-zone').textContent=Intl.DateTimeFormat().resolvedOptions().timeZone||'Device local time';
    const minute=Math.floor(now.getTime()/60000);if(minute===lastMinute||byId('hamclock').hidden)return;lastMinute=minute;
    const sun=solar.position(now);drawWorld(now,sun);
    byId('sun-altitude').textContent=home?`${solar.altitude(home.lat,home.lon,sun).toFixed(1)}° elevation`:'Set locator';
    const events=home?solar.sunEvents(home,now):[];
    for(const kind of ['sunrise','sunset']){const event=events.find(item=>item.kind===kind);byId(kind).textContent=event?`${utcDate(event.time)} ${utcTime(event.time).slice(0,5)}`:home?'None in next 24 h':'—';}
  }
  byId('fullscreen').addEventListener('click',async()=>{try{if(document.fullscreenElement)await document.exitFullscreen();else await byId('hamclock').requestFullscreen();}catch{byId('station-message').textContent='Fullscreen is unavailable in this browser.';}});
  document.querySelector('[data-panel="hamclock"]').addEventListener('click',tick);
  fetch('/world.json').then(response=>{if(!response.ok)throw new Error('Map unavailable');return response.json();}).then(data=>{geography=data;lastMinute=-1;tick();}).catch(()=>{lastMinute=-1;tick();});
  byId('refresh-weather').addEventListener('click',async()=>{
    const button=byId('refresh-weather');button.disabled=true;byId('weather-message').textContent='Fetching timestamped NOAA observations…';
    try{
      const response=await fetch('/api/spaceweather');if(!response.ok)throw new Error('Station could not fetch weather.');const data=await response.json();let errors=0;
      for(const [key,maxAge]of [['kp',6],['flux',30]]){
        const item=data[key];byId(key+'-value').textContent=item.value===null?'—':Number(item.value).toFixed(key==='kp'?2:1);
        if(item.error){errors++;byId(key+'-time').textContent='Unavailable · retry later';continue;}
        const observed=new Date(item.observed_at),age=(Date.now()-observed.getTime())/3600000;
        const ageLabel=age < -.25?' · check device clock':age>maxAge?' · STALE':'';
        byId(key+'-time').textContent=`${utcDate(observed)} ${utcTime(observed).slice(0,5)} UTC${ageLabel}`;
      }
      byId('weather-message').textContent=errors?'Some NOAA sources are unavailable. No substitute values are shown.':`NOAA observations · retrieved ${utcDate(new Date(data.fetched_at))} ${utcTime(new Date(data.fetched_at))} UTC. Kp and flux alone do not predict individual band openings.`;
    }catch(error){byId('weather-message').textContent=error.message+' Existing readings, if any, retain their observation timestamps.';}finally{button.disabled=false;}
  });
  tick();setInterval(tick,1000);
})();
