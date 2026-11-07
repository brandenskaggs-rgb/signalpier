/* Approximate solar geometry, Maidenhead locators, and great-circle navigation. */
(function(root){
  'use strict';
  const rad=Math.PI/180,deg=180/Math.PI,wrap=value=>((value%360)+360)%360;
  function position(date){
    const jd=date.getTime()/86400000+2440587.5,n=jd-2451545;
    const L=wrap(280.460+.9856474*n),g=wrap(357.528+.9856003*n)*rad;
    const lambda=(L+1.915*Math.sin(g)+.020*Math.sin(2*g))*rad;
    const epsilon=(23.439-.0000004*n)*rad;
    const ra=wrap(Math.atan2(Math.cos(epsilon)*Math.sin(lambda),Math.cos(lambda))*deg);
    const dec=Math.asin(Math.sin(epsilon)*Math.sin(lambda))*deg;
    const gmst=wrap(280.46061837+360.98564736629*n);
    return {lat:dec,lon:((ra-gmst+540)%360+360)%360-180,gmst};
  }
  function altitude(lat,lon,sun){
    return Math.asin(Math.max(-1,Math.min(1,Math.sin(lat*rad)*Math.sin(sun.lat*rad)+Math.cos(lat*rad)*Math.cos(sun.lat*rad)*Math.cos((lon-sun.lon)*rad))))*deg;
  }
  function fromGrid(grid){
    const value=grid.trim().toUpperCase();
    if(!/^[A-R]{2}[0-9]{2}(?:[A-X]{2}(?:[0-9]{2})?)?$/.test(value))throw new Error('Use a 4, 6, or 8 character Maidenhead locator, such as EN61 or IO91wm.');
    let lon=(value.charCodeAt(0)-65)*20-180+Number(value[2])*2;
    let lat=(value.charCodeAt(1)-65)*10-90+Number(value[3]);
    let width=2,height=1;
    if(value.length>=6){width/=24;height/=24;lon+=(value.charCodeAt(4)-65)*width;lat+=(value.charCodeAt(5)-65)*height;}
    if(value.length===8){width/=10;height/=10;lon+=Number(value[6])*width;lat+=Number(value[7])*height;}
    return {lat:lat+height/2,lon:lon+width/2,grid:value};
  }
  function route(a,b){
    const phi1=a.lat*rad,phi2=b.lat*rad,dl=(b.lon-a.lon)*rad,dp=phi2-phi1;
    const h=Math.sin(dp/2)**2+Math.cos(phi1)*Math.cos(phi2)*Math.sin(dl/2)**2;
    const distance=2*6371.0088*Math.asin(Math.sqrt(Math.min(1,Math.max(0,h))));
    const bearing=wrap(Math.atan2(Math.sin(dl)*Math.cos(phi2),Math.cos(phi1)*Math.sin(phi2)-Math.sin(phi1)*Math.cos(phi2)*Math.cos(dl))*deg);
    return {distance_km:distance,bearing_deg:distance<.001?null:bearing};
  }
  function sunEvents(point,date){
    const events=[];let previous=date.getTime(),prev=altitude(point.lat,point.lon,position(date))+.833;
    for(let i=1;i<=144;i++){
      const current=date.getTime()+i*600000,value=altitude(point.lat,point.lon,position(new Date(current)))+.833;
      if((prev<0)!==(value<0)){
        let lo=previous,hi=current;
        for(let j=0;j<16;j++){const mid=(lo+hi)/2,at=altitude(point.lat,point.lon,position(new Date(mid)))+.833;if((at<0)===(prev<0))lo=mid;else hi=mid;}
        events.push({kind:prev<0?'sunrise':'sunset',time:new Date((lo+hi)/2)});
      }
      previous=current;prev=value;
    }
    return events;
  }
  const api={position,altitude,fromGrid,route,sunEvents};
  if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.RadioSolar=api;
})(globalThis);
