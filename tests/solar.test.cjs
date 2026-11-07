const test=require('node:test'),assert=require('node:assert/strict'),solar=require('../static/solar.js');
test('Maidenhead locators resolve to known centers and reject invalid grids',()=>{
  assert.deepEqual(solar.fromGrid('JJ00'),{lat:.5,lon:1,grid:'JJ00'});
  const london=solar.fromGrid('IO91wm');assert.ok(Math.abs(london.lat-51.52)<.03);assert.ok(Math.abs(london.lon+.125)<.03);
  for(const value of ['ZZ99','AB','AA00YY','AA0000','JJ00aa123'])assert.throws(()=>solar.fromGrid(value));
});
test('Solstices and equinox have expected declination and subsolar longitude',()=>{
  const june=solar.position(new Date('2026-06-21T12:00:00Z')),dec=solar.position(new Date('2026-12-21T12:00:00Z'));
  assert.ok(Math.abs(june.lat-23.44)<.1);assert.ok(Math.abs(dec.lat+23.44)<.1);
  const equinox=solar.position(new Date('2026-03-20T12:00:00Z'));assert.ok(Math.abs(equinox.lat)<.3);assert.ok(Math.abs(equinox.lon)<3);
  assert.ok(solar.altitude(equinox.lat,equinox.lon,equinox)>89.99);
});
test('Great-circle distance and bearing agree with London to New York reference',()=>{
  const route=solar.route({lat:51.5074,lon:-.1278},{lat:40.7128,lon:-74.006});
  assert.ok(Math.abs(route.distance_km-5570)<10);assert.ok(Math.abs(route.bearing_deg-288.3)<.2);
  assert.equal(solar.route({lat:0,lon:0},{lat:0,lon:0}).bearing_deg,null);
});
test('Equatorial sunrise is near 06 UTC and polar summer has no crossings',()=>{
  const events=solar.sunEvents({lat:0,lon:0},new Date('2026-03-20T00:00:00Z'));
  assert.equal(events.length,2);assert.equal(events[0].kind,'sunrise');
  assert.ok(Math.abs(events[0].time.getUTCHours()+events[0].time.getUTCMinutes()/60-6)<.3);
  assert.equal(solar.sunEvents({lat:89,lon:0},new Date('2026-06-21T00:00:00Z')).length,0);
});
