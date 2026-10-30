const zone=document.querySelector('#id_timezone[data-detect="true"]');
if(zone)zone.value=Intl.DateTimeFormat().resolvedOptions().timeZone;
const locate=document.querySelector('#locate');
if(locate)locate.addEventListener('click',()=>{
 const status=document.querySelector('#location-status');
 if(!navigator.geolocation){status.textContent='Location unavailable. Enter your location manually or discover online bands.';return;}
 status.textContent='Waiting for your permission…';
 navigator.geolocation.getCurrentPosition(pos=>{
  document.querySelector('#id_latitude').value=pos.coords.latitude.toFixed(2);
  document.querySelector('#id_longitude').value=pos.coords.longitude.toFixed(2);
  status.textContent='Approximate coordinates filled in. Enable location discovery and save to use nearby search. Your coordinates stay private.';
 },()=>{status.textContent='Location was not shared. Manual entry and Online Worldwide still work.';},{enableHighAccuracy:false,timeout:10000,maximumAge:300000});
});
