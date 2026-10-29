/* Birth-data profiles, habit streaks and the personal astro-wellness plan.
 * Moved out of templates/index.html (B-17); behaviour unchanged. */
  document.addEventListener('DOMContentLoaded', function(){
    const loadBtn = document.getElementById('bd-load');
    const saveBtn = document.getElementById('bd-save');
    const genBtn = document.getElementById('bd-generate');
    const out = document.getElementById('wellness-output');
    const profileSelect = document.getElementById('bd-profile-select');
    const profileRenameBtn = document.getElementById('bd-profile-rename');
    const profileDefaultBtn = document.getElementById('bd-profile-default');
    const profileDeleteBtn = document.getElementById('bd-profile-delete');
    const profileExportBtn = document.getElementById('bd-profile-export');
    const profileImportBtn = document.getElementById('bd-profile-import-btn');
    const profileImportInput = document.getElementById('bd-profile-import');
    async function refreshProfileList(){
      try{
        const res = await fetchWithTimeout('/api/astro/profile?user_key=default');
        if(res.ok){
          const profiles = await res.json();
          profileSelect.innerHTML = '<option value="">-- Select saved profile --</option>';
          profiles.forEach(p=>{
            const d = p.data;
            const name = p.name || '';
            const label = `${name? name+': ':''}${d.date||'?' } ${d.city||''} ${p.created_at||''}`.trim();
            const opt = document.createElement('option');
            opt.value = p.id;
            opt.textContent = label + (p.is_default? ' ★': '');
            opt.dataset.profile = JSON.stringify(p);
            profileSelect.appendChild(opt);
          });
        }
      }catch{}
    }
    refreshProfileList().then(async ()=>{
      // Auto-load default profile if exists
      try{
        const res = await fetchWithTimeout('/api/astro/profile?user_key=default');
        if(res.ok){
          const profiles = await res.json();
          const def = profiles.find(p=>p.is_default);
          if(def){
            const d = def.data;
            if(d.date) document.getElementById('bd-date').value = d.date;
            if(d.time) document.getElementById('bd-time').value = d.time;
            if(d.gender) document.getElementById('bd-gender').value = d.gender;
            if(d.city) document.getElementById('bd-city').value = d.city;
            if(d.tz_hours) document.getElementById('tz-hours').value = d.tz_hours;
            if(d.tz_mins) document.getElementById('tz-mins').value = d.tz_mins;
            if(d.lat){ document.getElementById('lat-deg').value = d.lat.deg; document.getElementById('lat-min').value = d.lat.min; document.getElementById('lat-sec').value = d.lat.sec; }
            if(d.lon){ document.getElementById('lon-deg').value = d.lon.deg; document.getElementById('lon-min').value = d.lon.min; document.getElementById('lon-sec').value = d.lon.sec; }
            if(d.altitude) document.getElementById('bd-altitude').value = d.altitude;
            if(d.pressure) document.getElementById('bd-pressure').value = d.pressure;
            if(d.temp) document.getElementById('bd-temp').value = d.temp;
            localStorage.setItem('sbc_birth_profile', JSON.stringify(d));
          }
        }
      }catch{}
    });
    if(profileSelect){
      profileSelect.addEventListener('change', function(){
        const opt = this.options[this.selectedIndex];
        if(!opt.value) return;
        const p = JSON.parse(opt.dataset.profile);
        const d = p.data;
        if(d.date) document.getElementById('bd-date').value = d.date;
        if(d.time) document.getElementById('bd-time').value = d.time;
        if(d.gender) document.getElementById('bd-gender').value = d.gender;
        if(d.city) document.getElementById('bd-city').value = d.city;
        if(d.tz_hours) document.getElementById('tz-hours').value = d.tz_hours;
        if(d.tz_mins) document.getElementById('tz-mins').value = d.tz_mins;
        if(d.lat){ document.getElementById('lat-deg').value = d.lat.deg; document.getElementById('lat-min').value = d.lat.min; document.getElementById('lat-sec').value = d.lat.sec; }
        if(d.lon){ document.getElementById('lon-deg').value = d.lon.deg; document.getElementById('lon-min').value = d.lon.min; document.getElementById('lon-sec').value = d.lon.sec; }
        if(d.altitude) document.getElementById('bd-altitude').value = d.altitude;
        if(d.pressure) document.getElementById('bd-pressure').value = d.pressure;
        if(d.temp) document.getElementById('bd-temp').value = d.temp;
        localStorage.setItem('sbc_birth_profile', JSON.stringify(d));
      });
    }
    if(profileRenameBtn){
      profileRenameBtn.addEventListener('click', async function(){
        const id = profileSelect.value;
        if(!id) { alert('Select a profile first'); return; }
        const name = prompt('Enter profile name');
        if(!name) return;
        try{
          const res = await fetchWithTimeout('/api/astro/profile/'+id, {method:'PUT', headers:{'Content-Type':'application/json'}, body: JSON.stringify({name})});
          if(res.ok){
            await refreshProfileList();
            alert('Profile renamed');
          }else{ alert('Rename failed'); }
        }catch{ alert('Rename failed'); }
      });
    }
    if(profileDefaultBtn){
      profileDefaultBtn.addEventListener('click', async function(){
        const id = profileSelect.value;
        if(!id) { alert('Select a profile first'); return; }
        try{
          const res = await fetchWithTimeout('/api/astro/profile/'+id+'/default', {method:'POST'});
          if(res.ok){ alert('Set as default'); } else { alert('Failed'); }
        }catch{ alert('Failed'); }
      });
    }
    if(profileExportBtn){
      profileExportBtn.addEventListener('click', async function(){
        try{
          const res = await fetchWithTimeout('/api/astro/profile/export?user_key=default');
          if(res.ok){
            const data = await res.json();
            const blob = new Blob([JSON.stringify(data, null, 2)], {type:'application/json'});
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'sbc_profiles_export.json';
            a.click();
            URL.revokeObjectURL(url);
          }
        }catch{ alert('Export failed'); }
      });
    }
    if(profileImportBtn){
      profileImportBtn.addEventListener('click', function(){ profileImportInput.click(); });
      profileImportInput.addEventListener('change', async function(e){
        const file = e.target.files[0];
        if(!file) return;
        const text = await file.text();
        try{
          const data = JSON.parse(text);
          const res = await fetchWithTimeout('/api/astro/profile/import', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(data)});
          if(res.ok){
            alert('Import successful');
            await refreshProfileList();
          }else{ alert('Import failed'); }
        }catch{ alert('Import failed'); }
        e.target.value = '';
      });
    }
    if(profileDeleteBtn){
      profileDeleteBtn.addEventListener('click', async function(){
        const id = profileSelect.value;
        if(!id) { alert('Select a profile first'); return; }
        if(!confirm('Delete selected profile?')) return;
        try{
          const res = await fetchWithTimeout('/api/astro/profile/'+id, {method:'DELETE'});
          if(res.ok){
            await refreshProfileList();
            alert('Profile deleted');
          }else{
            alert('Delete failed');
          }
        }catch{ alert('Delete failed'); }
      });
    }
    if(loadBtn){
      loadBtn.addEventListener('click', async function(){
        try{
          const res = await fetchWithTimeout('/api/astro/profile?user_key=default');
          if(res.ok){
            const profiles = await res.json();
            if(profiles.length>0){
              const d = profiles[0].data;
              if(d.date) document.getElementById('bd-date').value = d.date;
              if(d.time) document.getElementById('bd-time').value = d.time;
              if(d.gender) document.getElementById('bd-gender').value = d.gender;
              if(d.city) document.getElementById('bd-city').value = d.city;
              if(d.tz_hours) document.getElementById('tz-hours').value = d.tz_hours;
              if(d.tz_mins) document.getElementById('tz-mins').value = d.tz_mins;
              if(d.lat){ document.getElementById('lat-deg').value = d.lat.deg; document.getElementById('lat-min').value = d.lat.min; document.getElementById('lat-sec').value = d.lat.sec; }
              if(d.lon){ document.getElementById('lon-deg').value = d.lon.deg; document.getElementById('lon-min').value = d.lon.min; document.getElementById('lon-sec').value = d.lon.sec; }
              if(d.altitude) document.getElementById('bd-altitude').value = d.altitude;
              if(d.pressure) document.getElementById('bd-pressure').value = d.pressure;
              if(d.temp) document.getElementById('bd-temp').value = d.temp;
              localStorage.setItem('sbc_birth_profile', JSON.stringify(d));
              alert('Latest profile loaded');
            }else{
              alert('No saved profiles');
            }
          }
        }catch{ alert('Load failed'); }
      });
    }
    if(saveBtn){
      saveBtn.addEventListener('click', async function(){
        const data = {
          date: document.getElementById('bd-date')?.value,
          time: document.getElementById('bd-time')?.value,
          gender: document.getElementById('bd-gender')?.value,
          city: document.getElementById('bd-city')?.value,
          tz_hours: document.getElementById('tz-hours')?.value,
          tz_mins: document.getElementById('tz-mins')?.value,
          lat: {deg: document.getElementById('lat-deg')?.value, min: document.getElementById('lat-min')?.value, sec: document.getElementById('lat-sec')?.value},
          lon: {deg: document.getElementById('lon-deg')?.value, min: document.getElementById('lon-min')?.value, sec: document.getElementById('lon-sec')?.value},
          altitude: document.getElementById('bd-altitude')?.value,
          pressure: document.getElementById('bd-pressure')?.value,
          temp: document.getElementById('bd-temp')?.value,
          saved_at: new Date().toISOString()
        };
        localStorage.setItem('sbc_birth_profile', JSON.stringify(data));
        try{
          const res = await fetchWithTimeout('/api/astro/profile', {
            method:'POST',
            headers:{'Content-Type':'application/json'},
            body: JSON.stringify(data)
          });
          if(res.ok){
            alert('Birth profile saved locally and on server');
          }else{
            alert('Saved locally; server save failed');
          }
        }catch{
          alert('Saved locally; server unavailable');
        }
      });
    }
      // Load saved profile on page load
    try{
      const saved = localStorage.getItem('sbc_birth_profile');
      if(saved){
        const d = JSON.parse(saved);
        if(d.date) document.getElementById('bd-date').value = d.date;
        if(d.time) document.getElementById('bd-time').value = d.time;
        if(d.gender) document.getElementById('bd-gender').value = d.gender;
        if(d.city) document.getElementById('bd-city').value = d.city;
        if(d.tz_hours) document.getElementById('tz-hours').value = d.tz_hours;
        if(d.tz_mins) document.getElementById('tz-mins').value = d.tz_mins;
        if(d.lat) { document.getElementById('lat-deg').value = d.lat.deg; document.getElementById('lat-min').value = d.lat.min; document.getElementById('lat-sec').value = d.lat.sec; }
        if(d.lon) { document.getElementById('lon-deg').value = d.lon.deg; document.getElementById('lon-min').value = d.lon.min; document.getElementById('lon-sec').value = d.lon.sec; }
        if(d.altitude) document.getElementById('bd-altitude').value = d.altitude;
        if(d.pressure) document.getElementById('bd-pressure').value = d.pressure;
        if(d.temp) document.getElementById('bd-temp').value = d.temp;
      }
    }catch{}
    // Sync habit streaks from server on load
    try{
      fetchWithTimeout('/api/habits/streaks?user_key=default').then(r=>r.json()).then(data=>{
        window.sbc_habit_server = data;
        // Reminder for missed habits
        if('Notification' in window && Notification.permission === 'granted'){
          const today = localTodayISO();
          const habits = ['meditation','steps','colour'];
          habits.forEach(h=>{
            const server = data[h];
            if(!server || !server.last || server.last !== today){
              const title = 'SBC Wellness Reminder';
              const body = `You haven’t logged ${h} today. Keep the streak!`;
              try{ new Notification(title, {body}); }catch{}
            }
          });
        }else if('Notification' in window && Notification.permission !== 'denied'){
          Notification.requestPermission().then(p=>{ if(p==='granted'){ /* reminders will fire on next load */ } });
        }
      });
    }catch{}
    if(!genBtn) return;
    const sunSigns = [
      {name:'Capricorn', start:[12,22], end:[1,19]},
      {name:'Aquarius', start:[1,20], end:[2,18]},
      {name:'Pisces', start:[2,19], end:[3,20]},
      {name:'Aries', start:[3,21], end:[4,19]},
      {name:'Taurus', start:[4,20], end:[5,20]},
      {name:'Gemini', start:[5,21], end:[6,20]},
      {name:'Cancer', start:[6,21], end:[7,22]},
      {name:'Leo', start:[7,23], end:[8,22]},
      {name:'Virgo', start:[8,23], end:[9,22]},
      {name:'Libra', start:[9,23], end:[10,22]},
      {name:'Scorpio', start:[10,23], end:[11,21]},
      {name:'Sagittarius', start:[11,22], end:[12,21]}
    ];
    function getSunSign(dateStr){
      if(!dateStr) return '-';
      const d = new Date(dateStr+'T00:00:00');
      const m = d.getMonth()+1;
      const day = d.getDate();
      for(const s of sunSigns){
        const [sm,sd]=s.start;
        const [em,ed]=s.end;
        if(sm<em || sm===em){
          if((m===sm && day>=sd)||(m===em && day<=ed)) return s.name;
        }else{
          if((m===sm && day>=sd)||(m===em && day<=ed)) return s.name;
        }
      }
      return '-';
    }
    const dayColours = ['Sunday','Monday','Tuesday','Wednesday','Thursday','Friday','Saturday'];
    const colourMap = {
      0:'Orange/Red',1:'White',2:'Red',3:'Green',4:'Yellow',5:'White',6:'Black'
    };
    function getTodayColour(){
      const today = new Date();
      return colourMap[today.getDay()];
    }
    genBtn.addEventListener('click', async function(){
      const dateVal = document.getElementById('bd-date')?.value;
      const timeVal = document.getElementById('bd-time')?.value;
      const gender = document.getElementById('bd-gender')?.value;
      const city = document.getElementById('bd-city')?.value;
      let tzH = document.getElementById('tz-hours')?.value;
      let tzM = document.getElementById('tz-mins')?.value;
      const sunSign = getSunSign(dateVal);
      const todayColour = getTodayColour();
      const todayName = dayColours[new Date().getDay()];
      let html = '<h3>Personal Astro-Wellness Plan</h3>';
      html += '<p><b>Birth data:</b> '+(dateVal||'-')+' '+(timeVal||'-')+' '+(city||'-')+' '+(gender||'-')+'</p>';
      html += '<p><b>Western Sun Sign:</b> '+sunSign+' <span style="opacity:.7">Vedic chart requires exact time/place for Moon, Rahu/Ketu.</span></p>';
      if(dateVal && timeVal){
        try{
          // Auto-detect timezone from lat/lon if available
          let tzName = null;
          const latDeg = parseFloat(document.getElementById('lat-deg')?.value||0);
          const latMin = parseFloat(document.getElementById('lat-min')?.value||0);
          const latSec = parseFloat(document.getElementById('lat-sec')?.value||0);
          const lonDeg = parseFloat(document.getElementById('lon-deg')?.value||0);
          const lonMin = parseFloat(document.getElementById('lon-min')?.value||0);
          const lonSec = parseFloat(document.getElementById('lon-sec')?.value||0);
          const latDec = Math.abs(latDeg)+latMin/60+latSec/3600;
          const lonDec = Math.abs(lonDeg)+lonMin/60+lonSec/3600;
          const latSign = latDeg<0?-1:1;
          const lonSign = lonDeg<0?-1:1;
          const latFinal = latSign*latDec;
          const lonFinal = lonSign*lonDec;
          if(Math.abs(latFinal)>0.1 && Math.abs(lonFinal)>0.1){
            try{
              const tzRes = await fetchWithTimeout('/api/tz/from_coords?lat='+latFinal+'&lon='+lonFinal);
              if(tzRes.ok){
                const tzData = await tzRes.json();
                tzName = tzData.timezone;
                // Get accurate offset from server
                if(dateVal && timeVal && tzName){
                  try{
                    const offRes = await fetchWithTimeout(`/api/tz/offset?tz=${encodeURIComponent(tzName)}&date=${encodeURIComponent(dateVal)}&time=${encodeURIComponent(timeVal)}`);
                    if(offRes.ok){
                      const offData = await offRes.json();
                      if(document.getElementById('tz-hours')) document.getElementById('tz-hours').value = offData.offset_hours;
                      if(document.getElementById('tz-mins')) document.getElementById('tz-mins').value = Math.abs(offData.offset_mins);
                    }
                  }catch{}
                }
              }
            }catch{}
          }
          let params;
          if(tzName){
            params = new URLSearchParams({date:dateVal,time:timeVal,tz:tzName});
          }else{
            const tzH = document.getElementById('tz-hours')?.value || '5';
            const tzM = document.getElementById('tz-mins')?.value || '30';
            params = new URLSearchParams({date:dateVal,time:timeVal,tz_hours:tzH,tz_mins:tzM});
          }
          const res = await fetchWithTimeout('/api/astro/personal?'+params.toString());
          if(res.ok){
            const data = await res.json();
            html += '<p><b>Vedic positions (sidereal):</b> Sun '+ (data.sun?.sign||'-') +' Nakshatra '+ (data.sun?.nakshatra||'-') +', Moon '+ (data.moon?.sign||'-') +' '+ (data.moon?.nakshatra||'-') +'</p>';
            html += '<p><b>Rahu/Ketu:</b> Rahu '+ (data.rahu?.sign||'-') +', Ketu '+ (data.ketu?.sign||'-') +'</p>';
            // Personal SBC overlay suggestion
            const moonNak = data.moon?.nakshatra || '-';
            html += `<p><b>Personal SBC Overlay:</b> Moon in ${moonNak}. This nakshatra aligns with the SBC border ring – monitor vedhas on the corresponding cell and Pancha-Shakha points for personal market timing.</p>`;
            // Update grid header with personal overlay badge
            try{
              const gridSub = document.getElementById('grid-sub');
              if(gridSub){
                gridSub.textContent = `Personal Moon: ${moonNak} • `;
              }
              // Attempt cell-level highlight
              setTimeout(()=>{
                try{
                  const walker = document.createTreeWalker(document.getElementById('grid')||document.body, NodeFilter.SHOW_TEXT);
                  const nodes = [];
                  let n;
                  while(n = walker.nextNode()){
                    if(n.nodeValue && n.nodeValue.includes(moonNak)){
                      nodes.push(n.parentElement);
                    }
                  }
                  const seen = new Set();
                  nodes.forEach(el=>{
                    let cur = el;
                    while(cur && cur !== document.body){
                      if(cur.classList && cur.classList.contains('grid-cell')){
                        if(!seen.has(cur)){
                          cur.classList.add('personal-highlight');
                          seen.add(cur);
                        }
                        break;
                      }
                      cur = cur.parentElement;
                    }
                  });
                }catch{}
              }, 500);
            }catch{}
            // Personal Natal Highlights table
            const planets = data.planets||[];
            const tbl = ['<table style="width:100%;font-size:12px;border-collapse:collapse"><thead><tr><th style="text-align:left;padding:4px">Planet</th><th style="text-align:left;padding:4px">Sign</th><th style="text-align:left;padding:4px">Nakshatra</th><th style="text-align:left;padding:4px">Pada</th></tr></thead><tbody>'];
            planets.forEach(p=>{
              tbl.push(`<tr><td style="padding:4px;border-top:1px solid var(--line)">${p.name}</td><td style="padding:4px;border-top:1px solid var(--line)">${p.sign||'-'}</td><td style="padding:4px;border-top:1px solid var(--line)">${p.nakshatra||'-'}</td><td style="padding:4px;border-top:1px solid var(--line)">${p.pada||'-'}</td></tr>`);
            });
            tbl.push('</tbody></table>');
            html += '<p><b>Personal Natal Highlights:</b></p>'+tbl.join('');
          }else{
            html += '<p><i>Astro API error</i></p>';
          }
        }catch(e){ html += '<p><i>Could not fetch astro data</i></p>'; }
      }
      html += '<div style="margin:8px 0"><button type="button" class="btn" id="log-meditation">Log 20 min Meditation</button> <span id="med-streak" style="margin-left:8px;opacity:.8"></span> <button type="button" class="btn" id="log-steps" style="margin-left:12px">Log 10k Steps</button> <span id="steps-streak" style="margin-left:8px;opacity:.8"></span> <button type="button" class="btn" id="log-colour" style="margin-left:12px">Log Today’s Colour</button> <span id="colour-streak" style="margin-left:8px;opacity:.8"></span> <button type="button" class="btn" id="weekly-summary" style="margin-left:12px">Weekly Summary</button> <button type="button" class="btn" id="export-habits" style="margin-left:12px">Export Habits CSV</button> <button type="button" class="btn" id="show-chart" style="margin-left:12px">7-day Chart</button></div><div id="habit-chart" style="margin-top:12px"></div>';
      html += '<ul>';
      html += '<li><b>Meditation:</b> 20 min daily breath-focus, same spot/time. First 40 days mind-clean up.</li>';
      html += '<li><b>Rahu-Ketu balance:</b> Ketu → meditation/trance; Rahu → 10k steps / gym daily.</li>';
      html += '<li><b>Colour for today ('+todayName+'):</b> '+todayColour+' – wear only if the ruling planet is strong in your chart.</li>';
      html += '<li><b>Wealth signs:</b> Check Taurus, Virgo, Capricorn strength in Vedic chart; strengthen via mantras/rituals.</li>';
      html += '<li><b>30-day plan:</b> Days 1-7 meditate, 8-14 white horse symbol, 15-21 silver square in wallet, 22-28 compute chart, 29-30 Rahu/Ketu remedy.</li>';
      html += '</ul>';
      html += '<p><i>Note: Spiritual/psychological guidance only. Consult a qualified astrologer and financial advisor.</i></p>';
      out.innerHTML = html;
      out.classList.remove('hidden');
      // Meditation streak handling
      try{
        const logBtn = out.querySelector('#log-meditation');
        const streakSpan = out.querySelector('#med-streak');
        const stepsBtn = out.querySelector('#log-steps');
        const stepsSpan = out.querySelector('#steps-streak');
        const colourBtn = out.querySelector('#log-colour');
        const colourSpan = out.querySelector('#colour-streak');
        const medKey = 'sbc_meditation_streak';
        const stepsKey = 'sbc_steps_streak';
        const colourKey = 'sbc_colour_streak';
        const medData = JSON.parse(localStorage.getItem(medKey)||'{"last":"", "streak":0}');
        const stepsData = JSON.parse(localStorage.getItem(stepsKey)||'{"last":"", "streak":0}');
        const colourData = JSON.parse(localStorage.getItem(colourKey)||'{"last":"", "streak":0}');
        const updateStreak = (data, span, habitKey)=>{
          let streak = data.streak;
          if(window.sbc_habit_server && window.sbc_habit_server[habitKey]){
            streak = window.sbc_habit_server[habitKey].streak;
          }
          const txt = `Streak: ${streak} day${streak!==1?'s':''}`;
          if(span) span.textContent = txt;
        };
        updateStreak(medData, streakSpan, 'meditation');
        updateStreak(stepsData, stepsSpan, 'steps');
        updateStreak(colourData, colourSpan, 'colour');
        updateStreak(stepsData, stepsSpan);
        updateStreak(colourData, colourSpan);
        if(logBtn){
          logBtn.addEventListener('click', async ()=>{
            const now = localTodayISO();
            if(medData.last !== now){
              if(medData.last){
                const prev = new Date(medData.last);
                const cur = new Date(now);
                const diff = (cur - prev)/86400000;
                medData.streak = diff===1 ? medData.streak+1 : diff>1?1: medData.streak;
              }else{
                medData.streak = 1;
              }
              medData.last = now;
              localStorage.setItem(medKey, JSON.stringify(medData));
              updateStreak(medData, streakSpan);
              try{ await fetchWithTimeout('/api/habits/log', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({habit_type:'meditation', date:now})}); }catch{}
              alert('Meditation logged! Keep the streak going.');
            }else{
              alert('Already logged today.');
            }
          });
        }
        if(stepsBtn){
          stepsBtn.addEventListener('click', async ()=>{
            const now = localTodayISO();
            if(stepsData.last !== now){
              if(stepsData.last){
                const prev = new Date(stepsData.last);
                const cur = new Date(now);
                const diff = (cur - prev)/86400000;
                stepsData.streak = diff===1 ? stepsData.streak+1 : diff>1?1: stepsData.streak;
              }else{
                stepsData.streak = 1;
              }
              stepsData.last = now;
              localStorage.setItem(stepsKey, JSON.stringify(stepsData));
              updateStreak(stepsData, stepsSpan);
              try{ await fetchWithTimeout('/api/habits/log', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({habit_type:'steps', date:now})}); }catch{}
              alert('Steps logged! Rahu balance maintained.');
            }else{
              alert('Already logged today.');
            }
          });
        }
        if(colourBtn){
          colourBtn.addEventListener('click', async ()=>{
            const now = localTodayISO();
            if(colourData.last !== now){
              if(colourData.last){
                const prev = new Date(colourData.last);
                const cur = new Date(now);
                const diff = (cur - prev)/86400000;
                colourData.streak = diff===1 ? colourData.streak+1 : diff>1?1: colourData.streak;
              }else{
                colourData.streak = 1;
              }
              colourData.last = now;
              localStorage.setItem(colourKey, JSON.stringify(colourData));
              updateStreak(colourData, colourSpan);
              try{ await fetchWithTimeout('/api/habits/log', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({habit_type:'colour', date:now})}); }catch{}
              alert('Today’s colour logged!');
            }else{
              alert('Already logged today.');
            }
          });
        }
        const weeklyBtn = out.querySelector('#weekly-summary');
        if(weeklyBtn){
          weeklyBtn.addEventListener('click', ()=>{
            alert(`Weekly Summary
Meditation streak: ${medData.streak} days, last: ${medData.last||'never'}
Steps streak: ${stepsData.streak} days, last: ${stepsData.last||'never'}
Colour streak: ${colourData.streak} days, last: ${colourData.last||'never'}`);
          });
        }
        const exportBtn = out.querySelector('#export-habits');
        if(exportBtn){
          exportBtn.addEventListener('click', ()=>{
            const csv = `Habit,Streak,Last Logged\nMeditation,${medData.streak},${medData.last||''}\nSteps,${stepsData.streak},${stepsData.last||''}\nColour,${colourData.streak},${colourData.last||''}`;
            const blob = new Blob([csv], {type:'text/csv'});
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'sbc_habits_export.csv';
            a.click();
            URL.revokeObjectURL(url);
          });
        }
        const chartBtn = out.querySelector('#show-chart');
        const chartDiv = out.querySelector('#habit-chart');
        if(chartBtn && chartDiv){
          chartBtn.addEventListener('click', async ()=>{
            try{
              const res = await fetchWithTimeout('/api/habits/history?user_key=default&days=7');
              if(!res.ok) return;
              const hist = await res.json();
              let html = '<div style="display:flex;gap:12px;margin-top:8px">';
              const habits = ['meditation','steps','colour'];
              const labels = ['Meditation','Steps','Colour'];
              const today = new Date();
              for(let i=6;i>=0;i--){
                const d = new Date(today);
                d.setDate(today.getDate()-i);
                const ds = isoDateOf(d);
                html += `<div style="text-align:center"><div style="font-size:10px;opacity:.7">${ds.slice(5)}</div>`;
                habits.forEach((h,idx)=>{
                  const cnt = (hist[h] && hist[h][ds]) ? 1 : 0;
                  html += `<div style="height:${cnt?24:8}px;width:24px;background:${cnt?'#4caf50':'#333'};margin:2px auto;border-radius:2px"></div>`;
                });
                html += `</div>`;
              }
      html += '</div>';
      chartDiv.innerHTML = html;
    }catch{}
  });
}
    }catch{}
    out.scrollIntoView({behavior:'smooth'});
  });
});

// The form's OK button (and Enter in any field) used to submit natively and reload the
// whole page. Submitting now runs "Generate Recommendations".
document.addEventListener('DOMContentLoaded', function(){
  const form = document.getElementById('birth-data-form');
  if (!form) return;
  form.addEventListener('submit', function(e){
    e.preventDefault();
    const gen = document.getElementById('bd-generate');
    if (gen) gen.click();
  });
});
