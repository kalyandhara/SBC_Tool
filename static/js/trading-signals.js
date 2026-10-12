/* Trading Signals panel: astro signal list, sector map, daily nakshatra sector dashboard.
 * Moved out of templates/index.html (B-17); behaviour unchanged. */
document.addEventListener('DOMContentLoaded', async ()=>{
  // Every row below comes from /api/astro/personal (build_response + Bhadra
  // calendar). Nothing is defaulted: a missing field shows as unavailable.
  // Hide details toggle with aria
  const toggleBtn = document.getElementById('toggle-trading-details');
  const detailsEl = document.getElementById('trading-signals-details');
  if(toggleBtn && detailsEl){
    toggleBtn.setAttribute('aria-controls','trading-signals-details');
    toggleBtn.setAttribute('aria-expanded','false');
    toggleBtn.addEventListener('click', ()=>{
      const hidden = detailsEl.classList.toggle('hidden');
      toggleBtn.setAttribute('aria-expanded', String(!hidden));
      toggleBtn.textContent = hidden ? 'Show Details' : 'Hide Details';
    });
  }

  const today = localTodayISO();
  let astro = null;
  try {
    const res = await fetchWithTimeout(`/api/astro/personal?date=${today}`);
    if(res.ok) astro = await res.json();
  } catch(e){}
  const scoreLabel = document.getElementById('astro-score-label');
  const scoreSub = document.getElementById('astro-score-sub');
  const list = document.getElementById('astro-signals-list');
  const fmtTime = iso => iso ? iso.slice(11,16) : '?';
  const fmtDay = iso => iso ? iso.slice(5,10) : '?';
  if(!astro || astro.error){
    if(scoreLabel) scoreLabel.textContent = 'UNAVAILABLE';
    if(scoreSub) scoreSub.textContent = 'Live panchanga could not be loaded.';
  } else {
    const vedhaNet = typeof astro.vedha_net === 'number' ? astro.vedha_net : null;
    const t = astro.tithi;
    const weekday = astro.weekday || '';
    const moonNak = astro.moon?.nakshatra || null;
    const tithiLabel = t ? `${t.paksha} ${t.name}` : 'tithi n/a';
    const signals = [];
    if(vedhaNet !== null){
      signals.push({icon: vedhaNet>0?'green':vedhaNet<0?'red':'grey',
        title:`SBC VEDHA NET ${vedhaNet.toFixed(2)}`,
        sub: vedhaNet>0?'benefic vedhas dominate':vedhaNet<0?'malefic vedhas dominate':'balanced'});
    }
    if(t){
      signals.push({icon: t.moon_benefic?'green':'red', title: tithiLabel.toUpperCase(), sub: t.moon_note || ''});
      if(weekday){
        const match = (t.group_weekdays||[]).includes(weekday);
        signals.push({icon: match?'green':'grey', title: weekday.toUpperCase(),
          sub: match ? `matches ${t.group} tithi weekdays` : `${t.group} tithi favours ${(t.group_weekdays||[]).join('/')||'—'}`});
      }
    }
    if(moonNak){
      signals.push({icon:'grey', title:`MOON IN ${moonNak.toUpperCase()}`, sub: astro.moon?.sign ? `${astro.moon.sign} (sidereal)` : ''});
    }
    const b = astro.bhadra;
    if(b){
      if(b.active_today){
        const spans = b.windows_today.map(w=>`${fmtDay(w.begin)} ${fmtTime(w.begin)}–${fmtDay(w.end)} ${fmtTime(w.end)}`).join(', ');
        signals.push({icon:'red', title:'BHADRA (VISHTI) TODAY', sub:`${spans} IST · avoid initiating major positions inside the window`});
      } else {
        signals.push({icon:'green', title:'NO BHADRA TODAY',
          sub: b.next ? `next: ${fmtDay(b.next.begin)} ${fmtTime(b.next.begin)}–${fmtDay(b.next.end)} ${fmtTime(b.next.end)} IST` : ''});
      }
    }
    if(scoreLabel){
      scoreLabel.textContent = vedhaNet===null ? '—' : vedhaNet>0?'BULLISH':vedhaNet<0?'BEARISH':'NEUTRAL';
      scoreLabel.insertAdjacentHTML('afterend', '<hr style="border:none;border-top:1px solid var(--border);margin:12px 0">');
    }
    if(scoreSub){
      scoreSub.textContent = [vedhaNet!==null?`Vedha net ${vedhaNet.toFixed(2)}`:null, weekday, tithiLabel, moonNak?`${moonNak} Nak`:null]
        .filter(Boolean).join(' · ');
    }
    if(list){
      list.innerHTML = signals.map(s=>`
        <div class="signal-row" style="display:flex;align-items:flex-start;gap:12px;padding:12px 0;border-bottom:1px solid var(--border)">
          <div class="signal-dot ${s.icon}" style="width:24px;height:24px;border-radius:50%;background:var(--dot-bg);display:flex;align-items:center;justify-content:center">●</div>
          <div><b>${esc(s.title)}</b><div style="opacity:.7;font-size:13px">${esc(s.sub)}</div></div>
        </div>
      `).join('');
    }
    const rz = document.getElementById('reversal-zone');
    const rd = document.getElementById('reversal-details');
    const wins = astro.reversal_windows || [];
    if(rz && rd){
      rz.classList.toggle('hidden', wins.length === 0);
      rd.innerHTML = wins.map(w=>`<div>${esc(w.level)} · ${esc(w.bias)} — ${esc(w.title)}</div>`).join('');
    }
  }
  // Sector map live from monthly heatmap
  try {
    const hmRes = await fetchWithTimeout(`/api/monthly_heatmap?date=${today}&days=1`);
    if(hmRes.ok){
      const hm = await hmRes.json();
      const sectors = [];
      const dates = hm.dates||[];
      const matrix = hm.matrix||{};
      const d = dates[0]||today;
      Object.entries(matrix).forEach(([sector, vals])=>{
        const v = vals[d]||0;
        const score = Math.min(10, Math.max(0, Math.round(Math.abs(v)*2)));
        const dir = v>=0?'up':'down';
        sectors.push({name: sector, score:`${score}/10`, dir});
      });
      const overall = document.getElementById('sector-map-overall');
      if(overall && sectors.length){
        const up = sectors.filter(x=>x.dir==='up').length, down = sectors.length - up;
        overall.textContent = up>down ? `BULLISH ${up}/${sectors.length}` : down>up ? `BEARISH ${down}/${sectors.length}` : 'MIXED';
      }
      const sm = document.getElementById('sector-map-items');
      if(sm){
        sm.innerHTML = sectors.slice(0,12).map(sec=>`
          <span style="display:inline-block;margin:4px 6px;padding:4px 8px;border-radius:4px;background:#1f2937;color:#e5e7eb;border:1px solid #374151">
            ${sec.dir==='up'?'▲':'▼'} ${sec.name} ${sec.score}
          </span>
        `).join('');
      }
    }
  } catch(e){}

});

// Daily Nakshatra Sector Dashboard
document.addEventListener('DOMContentLoaded', ()=>{
  const runBtn = document.getElementById('nakshatra-run');
  const chartBtn = document.getElementById('nakshatra-chart-run');
  const chartRange = document.getElementById('nakshatra-chart-range');
  const chartImg = document.getElementById('nakshatra-chart');
  const chartStatus = document.getElementById('nakshatra-chart-status');
  const dateEl = document.getElementById('nakshatra-date');
  const statusEl = document.getElementById('nakshatra-status');
  const contentEl = document.getElementById('nakshatra-content');
  if(!runBtn) return;
  if(!dateEl.value){
    const today = localTodayISO();
    dateEl.value = today;
  }
  async function generate(){
    if(!dateEl.value){ statusEl.textContent='Pick a date'; return; }
    statusEl.textContent='Computing...';
    try{
      const date = dateEl.value;
      const res = await fetchWithTimeout(`/api/daily_confluence?date=${encodeURIComponent(date)}&days=7`);
      if(!res.ok) throw new Error('API error');
      const data = await res.json();
      const nak = data.moon_nakshatra || 'Unknown';
      const keywords = data.keywords || [];
      const vedhaNet = Number(data.vedha_net) || 0;
      const direction = vedhaNet>0?'Bullish':vedhaNet<0?'Bearish':'Neutral';
      let html = `<h3>Date: ${date}</h3>`;
      html += `<p><b>Moon Nakshatra:</b> ${nak}</p>`;
      html += `<p><b>SBC Vedha Net:</b> ${vedhaNet.toFixed(2)} → ${direction}</p>`;
      html += `<p><b>Predicted Sector Keywords:</b> ${keywords.join(', ') || '—'}</p>`;
      html += `<p><b>Trading Bias:</b> ${direction} ${keywords.join(' / ') || ''}</p>`;
      // 7-day forecast table
      html += `<h4>7-Day Forecast</h4><table border="1" cellpadding="4" style="border-collapse:collapse;font-size:12px"><tr><th>Date</th><th>Nakshatra</th><th>Keywords</th><th>Vedha Net</th><th>Direction</th></tr>`;
      for (const row of data.forecast || []) {
        const n = row.nakshatra || '';
        const kws = (row.keywords||[]).join(', ');
        const vn = Number(row.vedha_net) || 0;
        html += `<tr><td>${row.date}</td><td>${n}</td><td>${kws}</td><td>${vn.toFixed(2)}</td><td>${row.direction}</td></tr>`;
      }
      html += `</table>`;
      html += `<button id="export-nakshatra-csv" class="btn" style="margin-top:8px">Export 7-Day CSV</button>`;
      contentEl.innerHTML = html;
      // export handler
      const expBtn = document.getElementById('export-nakshatra-csv');
      if(expBtn){
        expBtn.onclick = ()=>{
          // RFC 4180: quote a field only when it contains a comma, quote or
          // newline, and escape embedded quotes by doubling them.
          const csvField = v =>{
            const s = String(v ?? '');
            return /[",\n\r]/.test(s) ? '"'+s.replace(/"/g,'""')+'"' : s;
          };
          let csv = 'Date,Nakshatra,Keywords,Vedha Net,Direction\n';
          // build from the fetched data, not the rendered table
          for (const row of data.forecast || []) {
            csv += [
              row.date,
              row.nakshatra || '',
              (row.keywords||[]).join(', '),
              (Number(row.vedha_net)||0).toFixed(2),
              row.direction,
            ].map(csvField).join(',')+'\n';
          }
          const blob = new Blob([csv], {type:'text/csv'});
          const url = URL.createObjectURL(blob);
          const a = document.createElement('a');
          a.href = url;
          a.download = 'nakshatra_forecast.csv';
          a.click();
          URL.revokeObjectURL(url);
        };
      }
      statusEl.textContent='';
    }catch(e){
      statusEl.textContent='Failed: '+e.message;
    }
  }
  runBtn.addEventListener('click', generate);
  if(chartBtn){
    chartBtn.addEventListener('click', async ()=>{
      const date = dateEl.value;
      if(!date){ chartStatus.textContent = 'Pick a date before plotting.'; chartStatus.className = 'nifty-chart-status error'; return; }
      chartStatus.textContent = 'Generating native Python chart from NIFTY data...';
      chartStatus.className = 'nifty-chart-status';
      chartBtn.disabled = true;
      try{
        const res = await fetchWithTimeout(`/api/nakshatra_chart?date=${encodeURIComponent(date)}&months=${encodeURIComponent(chartRange.value)}`);
        if(!res.ok) throw new Error('chart unavailable');
        const blob = await res.blob();
        if(chartImg.dataset.objectUrl) URL.revokeObjectURL(chartImg.dataset.objectUrl);
        const objectUrl = URL.createObjectURL(blob);
        chartImg.dataset.objectUrl = objectUrl;
        chartImg.src = objectUrl;
        chartImg.classList.remove('hidden');
        chartStatus.textContent = 'Native Python chart ready.';
      }catch(e){
        chartStatus.textContent = 'Native chart unavailable. Check NIFTY data and try again.';
        chartStatus.className = 'nifty-chart-status error';
      }finally{ chartBtn.disabled = false; }
    });
  }
  generate();
});
