/* Birth-data forms: city search and longitude/latitude fill-in.
 * window.initBirthCity(opts) wires one form; Executive Overview and the
 * Navigator each call it with their own ids. Server strings use textContent. */
window.initBirthCity = function(opts){
  const el = (id) => (id ? document.getElementById(id) : null);
  const cityInput = el(opts.cityInput);
  if(!cityInput) return;
  const lonDeg = el(opts.lonDeg);
  const lonMin = el(opts.lonMin);
  const lonSec = el(opts.lonSec);
  const latDeg = el(opts.latDeg);
  const latMin = el(opts.latMin);
  const latSec = el(opts.latSec);
  const cityStatus = el(opts.status);
  const cityList = el(opts.list);
  const buttons = opts.buttons ? document.querySelectorAll(opts.buttons) : [];
  function toDMS(dec){
    // Round once, in whole arc-seconds, then split. Rounding the seconds
    // after flooring minutes turned 22.7 into 22°41'60" (float drift),
    // which the 0-59 seconds field rejects.
    const sign = dec < 0 ? -1 : 1;
    const total = Math.round(Math.abs(dec) * 3600);
    const d = Math.floor(total / 3600);
    const m = Math.floor((total % 3600) / 60);
    const s = total % 60;
    return {d: d*sign, m, s};
  }
  function fillCoords(lat, lon){
    const la = toDMS(lat);
    const lo = toDMS(lon);
    if(latDeg) latDeg.value = la.d;
    if(latMin) latMin.value = la.m;
    if(latSec) latSec.value = la.s;
    if(lonDeg) lonDeg.value = lo.d;
    if(lonMin) lonMin.value = lo.m;
    if(lonSec) lonSec.value = lo.s;
  }
  async function searchCities(q, country){
    if(!q || q.length < 2) return [];
    const url = new URL('/api/cities/search', window.location.origin);
    url.searchParams.set('q', q);
    if(country) url.searchParams.set('country', country);
    const res = await fetchWithTimeout(url);
    if(!res.ok) return [];
    return await res.json();
  }
  // B-14: results list instead of alert(); click (or Enter) picks a city.
  function setCityStatus(msg){ if(cityStatus) cityStatus.textContent = msg; }
  function hideCities(){ if(cityList){ cityList.classList.add('hidden'); cityList.replaceChildren(); } }
  function pickCity(r){
    const parts = [r.name, r.admin, r.country].filter(Boolean);
    cityInput.value = parts.join(', ');
    fillCoords(r.lat, r.lon);
    setCityStatus(`Selected ${parts.join(', ')} (${r.lat.toFixed(4)}, ${r.lon.toFixed(4)}${r.timezone ? ', ' + r.timezone : ''})`);
    hideCities();
    if(typeof opts.onSelect === 'function') opts.onSelect({lat: r.lat, lon: r.lon, timezone: r.timezone || ''});
  }
  function cityItem(r){
    const li = document.createElement('li');
    li.setAttribute('role', 'option');
    li.tabIndex = 0;
    const name = document.createElement('strong');
    name.textContent = String(r.name ?? '');
    const where = document.createElement('span');
    where.className = 'muted';
    where.textContent = [r.admin, r.country].filter(Boolean).join(', ');
    const pop = document.createElement('span');
    pop.className = 'city-pop';
    pop.textContent = Number(r.population || 0).toLocaleString();
    li.append(name, ' ', where, ' ', pop);
    li.addEventListener('click', () => pickCity(r));
    li.addEventListener('keydown', (e) => { if(e.key === 'Enter'){ e.preventDefault(); pickCity(r); } });
    return li;
  }
  function showCities(results){
    if(!cityList) return;
    if(!results.length){ hideCities(); setCityStatus('No matching city with 15,000+ people. Enter the coordinates by hand.'); return; }
    setCityStatus(`${results.length} match${results.length === 1 ? '' : 'es'}`);
    cityList.replaceChildren(...results.map(cityItem));
    cityList.classList.remove('hidden');
  }
  async function runCitySearch(country){
    const q = cityInput?.value?.trim();
    if(!q || q.length < 2){ hideCities(); setCityStatus('Type at least 2 letters of the city name.'); return; }
    try { showCities(await searchCities(q, country)); }
    catch { hideCities(); setCityStatus('City search failed. Try again.'); }
  }
  buttons.forEach(btn=>{
    btn.addEventListener('click', () => runCitySearch(btn.dataset.country || ''));
  });
  let cityTimer = null;
  cityInput.addEventListener('input', () => {
    clearTimeout(cityTimer);
    cityTimer = setTimeout(() => runCitySearch(''), 300);
  });
  cityInput.addEventListener('keydown', (e) => {
    if(e.key === 'Escape') hideCities();
    if(e.key === 'ArrowDown'){ const first = cityList?.querySelector('li'); if(first){ e.preventDefault(); first.focus(); } }
  });
};

document.addEventListener('DOMContentLoaded', function(){
  window.initBirthCity({
    cityInput: 'bd-city', status: 'bd-city-status', list: 'bd-city-results',
    lonDeg: 'lon-deg', lonMin: 'lon-min', lonSec: 'lon-sec',
    latDeg: 'lat-deg', latMin: 'lat-min', latSec: 'lat-sec',
    buttons: '#birth-data-form .city-buttons button',
  });
});

// Calendar/clock icons open the native picker; Cancel resets the form (were inline onclick).
document.addEventListener('DOMContentLoaded', function(){
  document.querySelectorAll('[data-picker-for]').forEach(function(icon){
    icon.addEventListener('click', function(){
      var input = document.getElementById(icon.dataset.pickerFor);
      if (!input) return;
      if (input.showPicker) { try { input.showPicker(); return; } catch (e) { /* not allowed: fall back */ } }
      input.focus();
    });
  });
  document.querySelectorAll('[data-reset-form]').forEach(function(btn){
    btn.addEventListener('click', function(){
      var form = document.getElementById(btn.dataset.resetForm);
      if (form) form.reset();
    });
  });
});
