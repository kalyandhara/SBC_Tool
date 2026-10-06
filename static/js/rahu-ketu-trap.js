/* Rahu/Ketu Trap Calendar panel.
 * Moved out of templates/index.html (B-17); behaviour unchanged. */
document.addEventListener('DOMContentLoaded',()=>{
  const runBtn=document.getElementById('rk-run');
  const startEl=document.getElementById('rk-start');
  const endEl=document.getElementById('rk-end');
  const heatDiv=document.getElementById('rk-heatmap');
  const escapeHtml=v=>String(v??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));
  if(!runBtn) return;
  const today=new Date();
  const fmt=d=>isoDateOf(d);
  const nseHolidays = new Set([
    '2025-01-26','2025-03-14','2025-03-31','2025-04-14','2025-04-18','2025-05-01','2025-08-15','2025-10-02','2025-10-20','2025-11-01','2025-11-05','2025-11-24','2025-12-25',
    '2026-01-26','2026-03-13','2026-03-30','2026-04-14','2026-04-17','2026-05-01','2026-08-15','2026-10-02','2026-10-19','2026-11-01','2026-11-04','2026-11-23','2026-12-25'
  ]);
  const isTradingDay = dStr=>{ const dt=new Date(dStr); const w=dt.getDay(); return w!==0 && w!==6 && !nseHolidays.has(dStr); };
  const nextTradingDays = (startDate, n)=>{ const dates=[]; let d=new Date(startDate); while(dates.length<n){ const ds=fmt(d); if(isTradingDay(ds)) dates.push(new Date(d)); d.setDate(d.getDate()+1); } return dates; };
  const tradingDates = nextTradingDays(today,5);
  const startDt = tradingDates[0];
  const endDt = tradingDates[4];
  if(!startEl.value) startEl.value=fmt(startDt);
  if(!endEl.value) endEl.value=fmt(endDt);
  const dayName=d=>new Date(d+'T00:00:00').toLocaleDateString('en-US',{weekday:'long'});
  const levelColor=s=>{
    if(s>=9) return '#ef4444';
    if(s>=6) return '#f97316';
    if(s>=3) return '#eab308';
    return '#22c55e';
  };
  runBtn.addEventListener('click',async()=>{
    heatDiv.innerHTML='<div style="padding:8px">Loading...</div>';
    try{
      const start=startEl.value; const end=endEl.value;
      if(!start||!end){ heatDiv.innerHTML='Select start and end dates.'; return; }
      const res=await fetchWithTimeout(`/api/rahu_ketu_trap_calendar?start=${encodeURIComponent(start)}&end=${encodeURIComponent(end)}`);
      if(!res.ok) throw new Error('API error');
      const data=await res.json();
      const calendar=data.calendar||[];
      if(!calendar.length){ heatDiv.innerHTML='<div style="padding:8px">No data</div>'; return; }
      // collect industries
      const indSet=new Set();
      calendar.forEach(day=>{ (day.signals||[]).forEach(s=>indSet.add(s.industry)); });
      const industries=[...indSet];
      // header
      let html=`<table style="border-collapse:collapse;font-size:11px;width:100%;overflow:auto"><thead><tr style="background:#0b1220">`;
      html+=`<th style="padding:4px;border:1px solid #334155;position:sticky;left:0;background:#0b1220">Date</th>`;
      html+=`<th style="padding:4px;border:1px solid #334155">Day</th>`;
      html+=`<th style="padding:4px;border:1px solid #334155">NSE?</th>`;
      industries.forEach(ind=>{ html+=`<th style="padding:4px;border:1px solid #334155;min-width:110px">${ind}</th>`; });
      html+=`<th style="padding:4px;border:1px solid #334155">Rahu/Ketu Status</th>`;
      html+=`</tr></thead><tbody>`;
      calendar.forEach(day=>{
        const date=day.date;  // the API returns NSE sessions only
        const dayNameStr=dayName(date);
        const nse='<span style="color:#22c55e">✓ Open</span>';
        html+=`<tr>`;
        html+=`<td style="padding:4px;border:1px solid #334155;position:sticky;left:0;background:#0b1220">${date}</td>`;
        html+=`<td style="padding:4px;border:1px solid #334155">${dayNameStr}</td>`;
        html+=`<td style="padding:4px;border:1px solid #334155">${nse}</td>`;
        // map signals by industry
        const sigMap={};
        (day.signals||[]).forEach(s=>{ sigMap[s.industry.toUpperCase()]=s; });
        industries.forEach(ind=>{
          const s=sigMap[ind.toUpperCase()];
          if(!s){ html+=`<td style="padding:4px;border:1px solid #334155;background:#1f2937">—</td>`; return; }
          const score=s.score||0;
          const level=s.level||'GREEN';
          const reasons=(s.reasons||[]).join(' · ');
          const title=`${s.ruling_planet} | Rahu:${s.rahu_nakshatra} Ketu:${s.ketu_nakshatra} Moon:${s.moon_nakshatra} | ${reasons}`;
          html+=`<td title="${title.replace(/"/g,'&quot;')}" style="padding:4px;border:1px solid #334155;background:${levelColor(score)};text-align:center">${score}<br><span style="font-size:9px;opacity:.8">${level}</span></td>`;
        });
        // status column: first signal's nodes
        const firstSig=(day.signals||[])[0];
        const rahuN=firstSig?.rahu_nakshatra||'-';
        const ketuN=firstSig?.ketu_nakshatra||'-';
        const stations=(day.node_stations||[]).map(t=>`<br><span style="color:#f97316">${escapeHtml(t)}</span>`).join('');
        html+=`<td style="padding:4px;border:1px solid #334155;font-size:10px">Rahu:${rahuN}<br>Ketu:${ketuN}${stations}</td>`;
        html+=`</tr>`;
      });
      html+=`</tbody></table>`;
      heatDiv.innerHTML=html;
    }catch(e){ heatDiv.innerHTML='Error loading calendar: '+e.message; }
  });
  runBtn.click();
});
