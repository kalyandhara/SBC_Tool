/* Trading Signals panel: astro score, moon backtests, walk-forward, nakshatra chart, sector map, predicted vs actual.
 * Moved out of templates/index.html (B-17); behaviour unchanged. */
document.addEventListener('DOMContentLoaded', async ()=>{
  // Every row below comes from /api/astro/personal (build_response + Bhadra
  // calendar). Nothing is defaulted: a missing field shows as unavailable.
  const today = localTodayISO();
  let astro = null;
  try {
    const res = await fetch(`/api/astro/personal?date=${today}`);
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

  // Integrate backtest accuracy into Astro Score display
  const astroScoreSub = document.getElementById('astro-score-sub');
  async function refreshAstroAccuracy(){
    if(!astroScoreSub) return;
    try{
      const res = await fetch(`/api/backtest/moon?ticker=^NSEI&multi_tf=true&regime=true&volume=true&vedha=false`);
      const data = await res.json();
      if(!data.error && data.samples>0){
        let acc = document.getElementById('astro-score-accuracy');
        if(!acc){ acc = document.createElement('div'); acc.id = 'astro-score-accuracy'; acc.style.opacity = '.7'; astroScoreSub.after(acc); }
        acc.textContent = `Moon backtest accuracy ${(data.accuracy*100).toFixed(1)}% (${data.samples} samples)`;
      }
    }catch(e){}
  }
  refreshAstroAccuracy();
  // Moon Rashi Backtest UI
  const backtestBtn = document.createElement('button');
  backtestBtn.textContent='Run Moon Backtest';
  backtestBtn.className='btn btn-sm';
  backtestBtn.style.marginLeft='8px';
  const sectorSelect = document.getElementById('nakshatra-sector-select');
  const controlsContainer = sectorSelect ? sectorSelect.closest('div') : null;
  const backtestResult = document.createElement('div');
  backtestResult.id='moon-backtest-result';
  backtestResult.style.marginTop='8px';
  backtestResult.style.fontSize='12px';
  backtestResult.style.color='#cbd5e1';
  const backtestTable = document.createElement('div');
  backtestTable.id='moon-backtest-table';
  backtestTable.style.marginTop='6px';
  backtestTable.style.maxHeight='200px';
  backtestTable.style.overflow='auto';
  backtestTable.style.fontSize='11px';
  const walkforwardDiv=document.createElement('div');
  walkforwardDiv.id='walkforward-div';
  walkforwardDiv.style.marginTop='8px';
  walkforwardDiv.style.fontSize='12px';
  walkforwardDiv.style.color='#cbd5e1';
  const   wfBtn=document.createElement('button');
  wfBtn.textContent='Walk-Forward Chart';
  wfBtn.className='btn btn-sm';
  wfBtn.style.marginLeft='8px';
  wfBtn.addEventListener('click', async ()=>{
    walkforwardDiv.textContent='Loading...';
    try{
      const res=await fetch('/api/backtest/walkforward?ticker=^NSEI&window=365&step=90');
      const data=await res.json();
      if(data.error){walkforwardDiv.textContent='Error: '+data.error; return;}
      let html='<table style="width:100%;border-collapse:collapse"><tr><th>Train Start</th><th>Test End</th><th>Samples</th><th>Accuracy</th></tr>';
      data.results.forEach(r=>{html+=`<tr><td>${r.train_start}</td><td>${r.test_end}</td><td>${r.samples}</td><td>${r.accuracy? (r.accuracy*100).toFixed(1)+'%':'-'} </td></tr>`;});
      html+='</table>';
      walkforwardDiv.innerHTML=html;
    }catch(e){walkforwardDiv.textContent='Error';}
  });
  const signalBtn=document.createElement('button');
  signalBtn.textContent='Live Moon Signals';
  signalBtn.className='btn btn-sm';
  signalBtn.style.marginLeft='8px';
  const signalDiv=document.createElement('div');
  signalDiv.id='moon-signals-div';
  signalDiv.style.marginTop='8px';
  signalDiv.style.fontSize='12px';
  signalDiv.style.color='#cbd5e1';
  signalBtn.addEventListener('click', async ()=>{
    signalDiv.textContent='Loading...';
    try{
      const sectorMapSig = {
        'Nifty Bank':'^NSEBANK',
        'Nifty IT':'^CNXIT',
        'Nifty Auto':'^CNXAUTO',
        'Nifty Metal':'^CNXMETAL',
        'Nifty FMCG':'^CNXFMCG',
        'Nifty Pharma':'^CNXPHARMA',
        'Nifty Energy':'^CNXENERGY',
        'Nifty Realty':'^CNXREALTY',
        'Nifty Large Caps':'^NSEI'
      };
      const tickerSig = sectorMapSig[sectorSelect.value] || '^NSEI';
      const res=await fetch(`/api/signal/moon?ticker=${encodeURIComponent(tickerSig)}&days=30`);
      const data=await res.json();
      if(data.error){signalDiv.textContent='Error: '+data.error; return;}
      let html='<table style="width:100%;border-collapse:collapse"><tr><th>Date</th><th>Rashi</th><th>Trend</th><th>Close</th></tr>';
      data.signals.forEach(s=>{html+=`<tr><td>${s.date}</td><td>${s.rashi}</td><td>${s.trend}</td><td>${s.close.toFixed(2)}</td></tr>`;});
      html+='</table>';
      signalDiv.innerHTML=html;
    }catch(e){signalDiv.textContent='Error';}
  });
  if(controlsContainer){
    controlsContainer.appendChild(backtestResult);
    controlsContainer.appendChild(backtestTable);
    controlsContainer.appendChild(wfBtn);
    controlsContainer.appendChild(walkforwardDiv);
    controlsContainer.appendChild(signalBtn);
    controlsContainer.appendChild(signalDiv);
  }
  const togglesDiv = document.createElement('div');
  togglesDiv.style.marginTop='6px';
  togglesDiv.style.fontSize='12px';
  const makeToggle=(label,key,def)=>{const id='bt-'+key; const wrap=document.createElement('label'); wrap.style.marginRight='12px'; const cb=document.createElement('input'); cb.type='checkbox'; cb.id=id; cb.checked=def; wrap.appendChild(cb); wrap.appendChild(document.createTextNode(' '+label)); togglesDiv.appendChild(wrap); return cb;};
  const multiCb=makeToggle('Multi-TF','multi',true);
  const regimeCb=makeToggle('Regime','regime',true);
  const volCb=makeToggle('Volume','volume',true);
  const vedhaCb=makeToggle('Vedha','vedha',false);
  if(controlsContainer){
    controlsContainer.insertBefore(togglesDiv, backtestResult);
  }
  let lastData=null;
  const exportBtn=document.createElement('button');
  exportBtn.textContent='Export CSV';
  exportBtn.className='btn btn-sm';
  exportBtn.style.marginLeft='8px';
  exportBtn.disabled=true;
  if(controlsContainer){
    controlsContainer.insertBefore(exportBtn, backtestResult);
  }
  exportBtn.addEventListener('click', ()=>{
    if(!lastData) return;
    const rows=[['date','expected','actual','match']].concat(lastData.results.map(r=>[r.date,r.expected,r.actual,r.match]));
    const csv=rows.map(r=>r.join(',')).join('\n');
    const blob=new Blob([csv],{type:'text/csv'});
    const url=URL.createObjectURL(blob);
    const a=document.createElement('a');
    a.href=url; a.download='moon_backtest.csv'; a.click();
    URL.revokeObjectURL(url);
  });
  backtestBtn.addEventListener('click', async ()=>{
    backtestResult.textContent='Running...';
    exportBtn.disabled=true;
    try{
      const sectorMap = {
        'Nifty Bank':'^NSEBANK',
        'Nifty IT':'^CNXIT',
        'Nifty Auto':'^CNXAUTO',
        'Nifty Metal':'^CNXMETAL',
        'Nifty FMCG':'^CNXFMCG',
        'Nifty Pharma':'^CNXPHARMA',
        'Nifty Energy':'^CNXENERGY',
        'Nifty Realty':'^CNXREALTY',
        'Nifty Large Caps':'^NSEI',
        'Nifty PSU': 'NSEI',
        'Nifty Infra': 'NSEI',
        'Nifty Gold': 'NIFTYGO',
        'Nifty Defense': 'INDIADEF'
      };
      const sector = sectorSelect.value;
      const ticker = sectorMap[sector] || '^NSEBANK';
      const res = await fetch(`/api/backtest/moon?ticker=${encodeURIComponent(ticker)}&multi_tf=${multiCb.checked}&regime=${regimeCb.checked}&volume=${volCb.checked}&vedha=${vedhaCb.checked}`);
      const data = await res.json();
      if(data.error){
        backtestResult.textContent='Error: '+data.error;
      }else{
        lastData=data;
        backtestResult.textContent=`Samples ${data.samples} | Correct ${data.correct} | Accuracy ${(data.accuracy*100).toFixed(2)}%`;
        exportBtn.disabled=false;
        const rows=data.results.slice(0,200);
        let html='<table style="width:100%;border-collapse:collapse"><thead><tr><th style="text-align:left;padding:2px">date</th><th>expected</th><th>actual</th><th>match</th></tr></thead><tbody>';
        rows.forEach(r=>{html+=`<tr><td style="padding:2px">${r.date}</td><td style="padding:2px;text-align:center">${r.expected}</td><td style="padding:2px;text-align:center">${r.actual}</td><td style="padding:2px;text-align:center">${r.match?'✓':'✗'}</td></tr>`;});
        html+='</tbody></table>';
        backtestTable.innerHTML=html;
      }
    }catch(e){
      backtestResult.textContent='Error: '+e;
    }
  });
  // Nakshatra Astro Chart loader
  let nakshatraChartInstance = null;
  document.getElementById('nakshatra-chart-load')?.addEventListener('click', async ()=>{
    const sector = document.getElementById('nakshatra-sector-select').value;
    const container = document.getElementById('nakshatra-astro-chart');
    // destroy previous instance
    if(nakshatraChartInstance){
      try{ nakshatraChartInstance.remove(); }catch(e){}
      nakshatraChartInstance = null;
    }
    container.innerHTML = '<div style="padding:20px">Loading '+sector+' astro chart...</div>';
    try {
      const tickerMap = {
        'Nifty Bank':'^NSEBANK',
        'Nifty IT':'^CNXIT',
        'Nifty Auto':'^CNXAUTO',
        'Nifty Metal':'^CNXMETAL',
        'Nifty FMCG':'^CNXFMCG',
        'Nifty Pharma':'^CNXPHARMA',
        'Nifty Energy':'^CNXENERGY',
        'Nifty Realty':'^CNXREALTY'
      };
      // Fallback aliases for yfinance
      const tickerFallback = {
        '^CNXIT':'^NSEIT',
        '^CNXAUTO':'^NSEAUTO',
        '^CNXMETAL':'^NSEMETAL',
        '^CNXFMCG':'^NSEFMCG',
        '^CNXPHARMA':'^NSEPHARMA',
        '^CNXENERGY':null,
        '^CNXREALTY':'^NSEREALTY'
      };
      let ticker = tickerMap[sector] || '^NSEBANK';
      let res = await fetch(`/api/price?ticker=${encodeURIComponent(ticker)}&days=90`);
      let candles = [];
      if(!res.ok || (await res.clone().json()).length===0){
        // try fallback
        const fb = tickerFallback[ticker];
        if(fb){
          ticker = fb;
          res = await fetch(`/api/price?ticker=${encodeURIComponent(ticker)}&days=90`);
        }
      }
      if(!res.ok) throw new Error('Price fetch failed');
      candles = await res.json();
      if(!candles.length) throw new Error('No price data for '+ticker);
      // Data-as-of stamp from the response headers (B-05)
      const priceAsOf = res.headers.get('X-Data-As-Of');
      const priceFresh = priceAsOf ? {as_of: priceAsOf, stale: res.headers.get('X-Data-Stale') === '1',
        expected: res.headers.get('X-Data-Expected'),
        sessions_behind: Number(res.headers.get('X-Data-Sessions-Behind') || 0)} : null;
      // Create lightweight chart if available
      if(window.LightweightCharts && container){
        container.innerHTML = '';
        const controlsBar = document.createElement('div');
        controlsBar.style.display='flex';
        controlsBar.style.gap='8px';
        controlsBar.style.alignItems='center';
        controlsBar.style.marginBottom='8px';
        controlsBar.style.fontSize='12px';
        controlsBar.innerHTML = `
          <label>Start <input id="ts-start" type="date" style="background:#0b1220;color:#cbd5e1;border:1px solid #334155;border-radius:4px;padding:2px 4px;"></label>
          <label>End <input id="ts-end" type="date" style="background:#0b1220;color:#cbd5e1;border:1px solid #334155;border-radius:4px;padding:2px 4px;"></label>
          <select id="ts-months" style="background:#0b1220;color:#cbd5e1;border:1px solid #334155;border-radius:4px;padding:2px 4px;">
            <option value="1">1 month</option>
            <option value="3" selected>3 months</option>
            <option value="6">6 months</option>
            <option value="12">12 months</option>
          </select>
          <button id="ts-load" class="btn btn-sm" style="background:#f59e0b;border:none;border-radius:4px;padding:4px 8px;cursor:pointer;">Load Chart</button>
          <span style="margin-left:8px;opacity:.7">Crash score</span>
        `;
        container.appendChild(controlsBar);
        if(priceFresh && window.SBCFreshness){
          const asof = document.createElement('div');
          asof.className = 'asof-slot';
          asof.innerHTML = SBCFreshness.badge(priceFresh, ticker);
          container.appendChild(asof);
        }
        // Wire Load Chart button to re-apply visible range
        const tsLoadBtn = controlsBar.querySelector('#ts-load');
        const tsStart = controlsBar.querySelector('#ts-start');
        const tsEnd = controlsBar.querySelector('#ts-end');
        const tsMonths = controlsBar.querySelector('#ts-months');
        const wrapper = document.createElement('div');
        wrapper.style.position='relative';
        wrapper.style.paddingTop='26px';
        container.appendChild(wrapper);
        const legend = document.createElement('div');
        legend.style.position='absolute';legend.style.top='8px';legend.style.right='8px';legend.style.background='rgba(0,0,0,0.6)';legend.style.padding='6px 10px';legend.style.borderRadius='6px';legend.style.fontSize='12px';legend.style.zIndex='10';
        const did = 'download-chart-'+Math.random().toString(36).slice(2);
        legend.innerHTML = `<span style="margin-left:4px">🟢 Bullish prediction</span> <span style="margin-left:12px">🔴 Bearish prediction</span> <span style="margin-left:12px">🟡 Reversal / risk alert</span> <span style="margin-left:12px">🟠 Crash calendar severity</span> <span style="margin-left:12px">● Price</span> <button id="${did}" class="btn btn-sm" style="margin-left:12px">Download CSV</button>`;
        wrapper.appendChild(legend);
        const chart = LightweightCharts.createChart(wrapper, {layout:{background:{type:'solid', color:'#0b1220'}}, width: Math.max(container.clientWidth||800,800), height:500});
        // Horizontal date bar
        const dateBar = document.createElement('div');
        dateBar.style.position='absolute';
        dateBar.style.top='0';
        dateBar.style.left='0';
        dateBar.style.right='0';
        dateBar.style.height='22px';
        dateBar.style.background='rgba(0,0,0,0.4)';
        dateBar.style.color='#cbd5e1';
        dateBar.style.fontSize='11px';
        dateBar.style.display='flex';
        dateBar.style.alignItems='center';
        dateBar.style.padding='0 8px';
        dateBar.style.justifyContent='space-between';
        dateBar.style.zIndex='5';
        const rangeLabel = document.createElement('span');
        rangeLabel.textContent='Loading range...';
        const presetBox = document.createElement('div');
        ['1M','3M','6M','1Y'].forEach(p=>{
          const b=document.createElement('button');
          b.textContent=p;
          b.style.marginLeft='6px';
          b.style.padding='2px 6px';
          b.style.fontSize='10px';
          b.style.background='#f59e0b';
          b.style.border='none';
          b.style.borderRadius='4px';
          b.style.cursor='pointer';
          b.onclick=()=>{ setRange(p); };
          presetBox.appendChild(b);
        });
        dateBar.appendChild(rangeLabel);
        dateBar.appendChild(presetBox);
        wrapper.appendChild(dateBar);
        nakshatraChartInstance = chart;
        // Resize observer
        const ro = new ResizeObserver(entries=>{
          for(const entry of entries){
            const {width} = entry.contentRect;
            chart.applyOptions({width: width});
          }
        });
        ro.observe(wrapper);
        const candlestickSeries = chart.addCandlestickSeries();
        candlestickSeries.setData(candles);
        // Fetch SBC vedha daily for selected sector
        const vedhaRes = await fetch(`/api/vedha_daily?sector=${encodeURIComponent(sector)}&days=90`);
        const vedhaData = await vedhaRes.json();
        // Vedha line disabled to avoid scale distortion; use markers only
        // const vedhaSeries = chart.addLineSeries({color:'#22c55e', lineWidth:2});
        // Background severity bands similar to Chart & Timing
        const severitySeries = chart.addHistogramSeries({
          priceFormat: {type:'price', precision:0},
          priceScaleId: 'right',
          color: '#ef4444',
          priceScale: {scaleMargins:{top:0.8,bottom:0.2}, visible:false}
        });
        const severityData = candles.map((c,i)=>{
          const v = vedhaData[i];
          const score = v && typeof v.score==='number' ? v.score : 0;
          // Map score to severity height
          const severity = Math.abs(score)*500;
          return {time:c.time, value: severity, color: score>=0 ? '#22c55e' : '#ef4444'};
        });
        severitySeries.setData(severityData);
        document.getElementById(did)?.addEventListener('click', ()=>{
          const rows = [['date','open','high','low','close','vedha','nakshatra_idx']];
          candles.forEach((c,i)=>{
            const v = vedhaData[i]||{};
            rows.push([new Date(c.time*1000).toISOString().split('T')[0],c.open,c.high,c.low,c.close,v.score||'',v.nakshatra_idx||'']);
          });
          const csv = rows.map(r=>r.join(',')).join('\n');
          const blob = new Blob([csv],{type:'text/csv'});
          const a = document.createElement('a');
          a.href = URL.createObjectURL(blob);
          a.download = `${sector.replace(/\s+/g,'_')}_astro_chart.csv`;
          a.click();
        });
        // Nakshatra markers - throttled to avoid clutter
        const nakshatras = ['Ashwini','Bharani','Krittika','Rohini','Mrigashira','Ardra','Punarvasu','Pushya','Ashlesha','Magha','Purva Phalguni','Uttara Phalguni','Hasta','Chitra','Swati','Vishakha','Anuradha','Jyeshtha','Mula','Purva Ashadha','Uttara Ashadha','Shravana','Dhanishta','Shatabhisha','Purva Bhadrapada','Uttara Bhadrapada','Revati'];
        const markers = candles.map((c,i)=>{
          const v = vedhaData[i];
          if(!v || v.score==null || v.nakshatra_idx==null) return null;
          // One marker per candle, arrow up/down based on vedha score
          return {
            time: c.time,
            position: v.score>=0 ? 'aboveBar' : 'belowBar',
            color: v.score>=0 ? '#22c55e' : '#ef4444',
            shape: v.score>=0 ? 'arrowUp' : 'arrowDown',
            text: ''
          };
        }).filter(Boolean);
        candlestickSeries.setMarkers(markers);
        // Default window: adaptive to data, 1 month prior to last available candle
        const lastCandleTime = Math.max(...candles.map(c=>c.time));
        const firstCandleTime = Math.min(...candles.map(c=>c.time));
        const oneMonthSec = 30*86400;
        const defaultFrom = lastCandleTime - oneMonthSec;
        const finalFrom = Math.max(defaultFrom, firstCandleTime);
        chart.timeScale().setVisibleRange({from: finalFrom, to: lastCandleTime});
        // Wire controls bar Load button to re-fetch and re-render
        if(tsLoadBtn){
          tsLoadBtn.addEventListener('click', async ()=>{
            const startVal = tsStart.value;
            const endVal = tsEnd.value;
            let startParam = startVal;
            let endParam = endVal;
            if(!startVal || !endVal){
              const months = parseInt(tsMonths.value)||3;
              const days = months*30;
              const endDate = new Date(lastCandleTime*1000);
              const startDate = new Date(endDate.getTime() - days*86400000);
              startParam = startDate.toISOString().slice(0,10);
              endParam = endDate.toISOString().slice(0,10);
              tsStart.value = startParam;
              tsEnd.value = endParam;
            }
            try{
              // Re-fetch price
              let priceUrl = `/api/price?ticker=${encodeURIComponent(ticker)}&start=${encodeURIComponent(startParam)}&end=${encodeURIComponent(endParam)}`;
              let resP = await fetch(priceUrl);
              if(!resP.ok) throw new Error('Price re-fetch failed');
              const newCandles = await resP.json();
              if(!newCandles.length) throw new Error('No price data for range');
              candlestickSeries.setData(newCandles);
              // Re-fetch vedha
              const vedhaUrl = `/api/vedha_daily?sector=${encodeURIComponent(sector)}&start=${encodeURIComponent(startParam)}&end=${encodeURIComponent(endParam)}`;
              const resV = await fetch(vedhaUrl);
              const vedhaDataNew = await resV.json();
              // Update markers
              const markersNew = newCandles.map((c,i)=>{
                const v = vedhaDataNew[i];
                if(!v || v.score==null || v.nakshatra_idx==null) return null;
                return {
                  time: c.time,
                  position: v.score>=0 ? 'aboveBar' : 'belowBar',
                  color: v.score>=0 ? '#22c55e' : '#ef4444',
                  shape: v.score>=0 ? 'arrowUp' : 'arrowDown',
                  text: ''
                };
              }).filter(Boolean);
              candlestickSeries.setMarkers(markersNew);
              // Update severity
              const severityDataNew = newCandles.map((c,i)=>{
                const v = vedhaDataNew[i];
                const score = v && typeof v.score==='number' ? v.score : 0;
                const severity = Math.abs(score)*500;
                return {time:c.time, value: severity, color: score>=0 ? '#22c55e' : '#ef4444'};
              });
              severitySeries.setData(severityDataNew);
              // Update visible range
              const first = Math.min(...newCandles.map(c=>c.time));
              const last = Math.max(...newCandles.map(c=>c.time));
              chart.timeScale().setVisibleRange({from:first, to:last});
            }catch(e){
              console.error(e);
              alert('Failed to reload chart: '+e);
            }
          });
          // Pre-fill dates
          tsStart.value = new Date(lastCandleTime*1000 - oneMonthSec*1000).toISOString().slice(0,10);
          tsEnd.value = new Date(lastCandleTime*1000).toISOString().slice(0,10);
        }
        // Update date bar on range change
        const updateRangeLabel = (range)=>{
          if(range){
            const from = new Date(range.from*1000).toLocaleDateString();
            const to = new Date(range.to*1000).toLocaleDateString();
            rangeLabel.textContent = `${from}  →  ${to}`;
          }
        };
        chart.timeScale().subscribeVisibleTimeRangeChange(updateRangeLabel);
        const setRange = (preset)=>{
          const daysMap={ '1M':60,'3M':180,'6M':360,'1Y':730 };
          const days = daysMap[preset]||180;
          const firstCandleTime = Math.min(...candles.map(c=>c.time));
          const lastCandleTime = Math.max(...candles.map(c=>c.time));
          const half = Math.floor(days*86400/2);
          let from = lastCandleTime - half;
          let to = lastCandleTime + half;
          from = Math.max(from, firstCandleTime);
          to = Math.min(to, lastCandleTime);
          chart.timeScale().setVisibleRange({from, to});
        };
        // Proper hover tooltip
        const tooltip = document.createElement('div');
        tooltip.style.position='absolute';
        tooltip.style.pointerEvents='none';
        tooltip.style.background='rgba(0,0,0,0.85)';
        tooltip.style.color='#fff';
        tooltip.style.padding='6px 8px';
        tooltip.style.borderRadius='6px';
        tooltip.style.fontSize='12px';
        tooltip.style.display='none';
        tooltip.style.zIndex='1000';
        wrapper.appendChild(tooltip);
        chart.subscribeCrosshairMove(param=>{
          if(!param.time || !param.seriesPricesValue) { tooltip.style.display='none'; return; }
          const v = vedhaData.find(v=> new Date(v.date).getTime()/1000 === param.time);
          const nakName = v && v.nakshatra_idx!=null ? nakshatras[v.nakshatra_idx%27] : '';
          const score = v && v.score!=null ? v.score.toFixed(2) : '—';
          tooltip.innerHTML = `Date: ${new Date(param.time*1000).toLocaleDateString()}<br>Vedha: ${score}<br>Nakshatra: ${nakName}`;
          const coords = param.point;
          if(coords){
            tooltip.style.left = (coords.x+10)+'px';
            tooltip.style.top = (coords.y+10)+'px';
            tooltip.style.display='block';
          }
        });
      } else {
        container.innerHTML = '<div style="padding:20px">Chart library not available.</div>';
      }
    } catch(e){
      container.innerHTML = '<div style="padding:20px;color:red">Failed: '+e+'</div>';
    }
  });

  // Sector map live from monthly heatmap
  try {
    const hmRes = await fetch(`/api/monthly_heatmap?date=${today}&days=1`);
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
      const res = await fetch(`/api/daily_confluence?date=${encodeURIComponent(date)}&days=7`);
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
        const res = await fetch(`/api/nakshatra_chart?date=${encodeURIComponent(date)}&months=${encodeURIComponent(chartRange.value)}`);
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
  // Predicted vs Actual chart loader for Trading Signals Astro Technical
  (async ()=>{
    const loadBtn = document.getElementById('trading-predicted-actual-load');
    if(!loadBtn) return;
    const sectorSelect = document.getElementById('nakshatra-sector-select');
    const topDiv = document.getElementById('predicted-actual-top');
    const bottomDiv = document.getElementById('predicted-actual-bottom');
    let topChart, bottomChart, topSeries, bottomSeries;
    loadBtn.addEventListener('click', async ()=>{
      try{
        const sector = sectorSelect?.value || 'Nifty Large Caps';
        const tickerMap = {
          'Nifty Bank':'^NSEBANK','Nifty IT':'^CNXIT','Nifty Auto':'^CNXAUTO',
          'Nifty Metal':'^CNXMETAL','Nifty FMCG':'^CNXFMCG','Nifty Pharma':'^CNXPHARMA',
          'Nifty Energy':'^CNXENERGY','Nifty Realty':'^CNXREALTY','Nifty Large Caps':'^NSEI'
        };
        const ticker = tickerMap[sector] || '^NSEI';
        const dateEl = document.getElementById('date');
        const selDate = dateEl?.value || localTodayISO();
        const priceRes = await fetch(`/api/price?ticker=${encodeURIComponent(ticker)}&start=${encodeURIComponent(selDate)}&end=${encodeURIComponent(selDate)}&interval=3m`);
        const candles = await priceRes.json();
        const projRes = await fetch(`/api/intraday_projection?sector=${encodeURIComponent(sector)}&date=${selDate}`);
        let proj = [];
        try{ proj = await projRes.json(); }catch(e){ proj = []; }
        if(!topChart && window.LightweightCharts && topDiv && bottomDiv){
          topChart = LightweightCharts.createChart(topDiv,{layout:{background:{type:'solid',color:'#0b1220'}},width:topDiv.clientWidth,height:300});
          bottomChart = LightweightCharts.createChart(bottomDiv,{layout:{background:{type:'solid',color:'#0b1220'}},width:bottomDiv.clientWidth,height:340});
          topSeries = topChart.addCandlestickSeries({upColor:'#22c55e',downColor:'#ef4444',borderVisible:false,wickUpColor:'#22c55e',wickDownColor:'#ef4444'});
          bottomSeries = bottomChart.addCandlestickSeries();
          // sync time scales
          topChart.timeScale().subscribeVisibleTimeRangeChange(range=>{
            if(range && bottomChart) bottomChart.timeScale().setVisibleRange(range);
          });
          bottomChart.timeScale().subscribeVisibleTimeRangeChange(range=>{
            if(range && topChart) topChart.timeScale().setVisibleRange(range);
          });
          // sync crosshair - optional; keep simple time sync
          // topChart.subscribeCrosshairMove(param=>{
          //   if(bottomChart && param.time) bottomChart.timeScale().setVisibleRange(bottomChart.timeScale().getVisibleRange()||{from:param.time-3600,to:param.time+3600});
          // });
          // bottomChart.subscribeCrosshairMove(param=>{
          //   if(topChart && param.time) topChart.timeScale().setVisibleRange(topChart.timeScale().getVisibleRange()||{from:param.time-3600,to:param.time+3600});
          // });
          const ro = new ResizeObserver(()=>{
            topChart.applyOptions({width:topDiv.clientWidth});
            bottomChart.applyOptions({width:bottomDiv.clientWidth});
          });
          ro.observe(topDiv); ro.observe(bottomDiv);
        }
        const rawPoints = Array.isArray(proj.points) ? proj.points : (Array.isArray(proj.hours) ? proj.hours : []);
        const predPoints = rawPoints.map(p=>{const t = typeof p.time==='number' ? p.time : Math.floor(new Date(p.time).getTime()/1000); const v = p.score ?? p.projection ?? 0; return {time:t,open:v,high:v,low:v,close:v};});
        if(predPoints.length){ topSeries.setData(predPoints); }else{
          const vedhaRes = await fetch(`/api/vedha_daily?sector=${encodeURIComponent(sector)}&days=90`);
          const vedha = await vedhaRes.json();
          const placeholder = candles.slice(0,100).map((c,i)=>{const v=(vedha[i]?.score||0)*100; return {time:c.time,open:v,high:v,low:v,close:v};});
          topSeries.setData(placeholder);
        }
        bottomSeries.setData(candles);
        topChart.timeScale().fitContent();
        bottomChart.timeScale().fitContent();
      }catch(e){ console.error('Predicted vs Actual load error',e); alert('Failed to load Predicted vs Actual'); }
    });
  })();
});
