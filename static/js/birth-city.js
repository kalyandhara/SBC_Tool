/* Birth-data form: city search and longitude/latitude fill-in.
 * Moved out of templates/index.html (B-17); behaviour unchanged. */
document.addEventListener('DOMContentLoaded', function(){
  const cityInput = document.getElementById('bd-city');
  const lonDeg = document.getElementById('lon-deg');
  const lonMin = document.getElementById('lon-min');
  const lonSec = document.getElementById('lon-sec');
  const latDeg = document.getElementById('lat-deg');
  const latMin = document.getElementById('lat-min');
  const latSec = document.getElementById('lat-sec');
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
    const res = await fetch(url);
    if(!res.ok) return [];
    return await res.json();
  }
  // B-14: results list instead of alert(); click (or Enter) picks a city.
  const cityStatus = document.getElementById('bd-city-status');
  const cityList = document.getElementById('bd-city-results');
  const escHtml = (v) => String(v ?? '').replace(/[&<>"']/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));
  function setCityStatus(msg){ if(cityStatus) cityStatus.textContent = msg; }
  function hideCities(){ if(cityList){ cityList.classList.add('hidden'); cityList.innerHTML = ''; } }
  function pickCity(r){
    const parts = [r.name, r.admin, r.country].filter(Boolean);
    cityInput.value = parts.join(', ');
    fillCoords(r.lat, r.lon);
    setCityStatus(`Selected ${parts.join(', ')} (${r.lat.toFixed(4)}, ${r.lon.toFixed(4)}${r.timezone ? ', ' + r.timezone : ''})`);
    hideCities();
  }
  function showCities(results){
    if(!cityList) return;
    if(!results.length){ hideCities(); setCityStatus('No matching city with 15,000+ people. Enter the coordinates by hand.'); return; }
    setCityStatus(`${results.length} match${results.length === 1 ? '' : 'es'}`);
    cityList.innerHTML = results.map((r, i) => `
      <li role="option" tabindex="0" data-i="${i}">
        <strong>${escHtml(r.name)}</strong> <span class="muted">${escHtml([r.admin, r.country].filter(Boolean).join(', '))}</span>
        <span class="city-pop">${Number(r.population || 0).toLocaleString()}</span>
      </li>`).join('');
    cityList.classList.remove('hidden');
    cityList.querySelectorAll('li').forEach(li => {
      const r = results[Number(li.dataset.i)];
      li.addEventListener('click', () => pickCity(r));
      li.addEventListener('keydown', (e) => { if(e.key === 'Enter'){ e.preventDefault(); pickCity(r); } });
    });
  }
  async function runCitySearch(country){
    const q = cityInput?.value?.trim();
    if(!q || q.length < 2){ hideCities(); setCityStatus('Type at least 2 letters of the city name.'); return; }
    try { showCities(await searchCities(q, country)); }
    catch { hideCities(); setCityStatus('City search failed. Try again.'); }
  }
  document.querySelectorAll('.city-buttons button').forEach(btn=>{
    btn.addEventListener('click', () => runCitySearch(btn.dataset.country || ''));
  });
  let cityTimer = null;
  cityInput?.addEventListener('input', () => {
    clearTimeout(cityTimer);
    cityTimer = setTimeout(() => runCitySearch(''), 300);
  });
  cityInput?.addEventListener('keydown', (e) => {
    if(e.key === 'Escape') hideCities();
    if(e.key === 'ArrowDown'){ const first = cityList?.querySelector('li'); if(first){ e.preventDefault(); first.focus(); } }
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
