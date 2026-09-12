/**
 * Astro Plot Chart - TradingView-style planetary time-series visualization
 * Renders: planet tracks, nakshatra bands, house bands, retrograde periods,
 * combustion zones, event markers, aspect timelines
 */

class AstroPlotChart {
    constructor(canvasId, data) {
        this.canvas = document.getElementById(canvasId);
        this.ctx = this.canvas.getContext('2d');
        this.data = data;
        this.dpr = window.devicePixelRatio || 1;
        
        // Chart dimensions
        this.margin = { top: 40, right: 120, bottom: 80, left: 100 };
        this.resize();
        
        // State
        this.hoveredPoint = null;
        this.selectedPlanet = null;
        this.showNakshatras = true;
        this.showHouses = true;
        this.showRetrograde = true;
        this.showCombustion = true;
        this.showEvents = true;
        this.showAspects = true;
        
        // Planet colors (from data)
        this.planetColors = data.planet_colors || {
            "Sun": "#FFD700", "Moon": "#C0C0C0", "Mars": "#FF4444", "Mercury": "#00BFFF",
            "Jupiter": "#FF8C00", "Venus": "#00FF7F", "Saturn": "#808080", "Rahu": "#8B00FF", "Ketu": "#FF00FF",
        };
        
        this.planetOrder = data.planets_order || [
            "Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"
        ];
        
        this.initCanvas();
        this.bindEvents();
        this.render();
    }
    
    resize() {
        const rect = this.canvas.parentElement.getBoundingClientRect();
        this.width = Math.max(600, rect.width - 2);
        this.height = 480;
        this.canvas.width = this.width * this.dpr;
        this.canvas.height = this.height * this.dpr;
        this.canvas.style.width = this.width + 'px';
        this.canvas.style.height = this.height + 'px';
        this.ctx.scale(this.dpr, this.dpr);
        
        // Plot area
        this.plotLeft = this.margin.left;
        this.plotRight = this.width - this.margin.right;
        this.plotTop = this.margin.top;
        this.plotBottom = this.height - this.margin.bottom;
        this.plotWidth = this.plotRight - this.plotLeft;
        this.plotHeight = this.plotBottom - this.plotTop;
    }
    
    initCanvas() {
        this.canvas.style.cursor = 'crosshair';
    }
    
    bindEvents() {
        this.canvas.addEventListener('mousemove', (e) => this.onMouseMove(e));
        this.canvas.addEventListener('mouseleave', () => this.onMouseLeave());
        this.canvas.addEventListener('click', (e) => this.onClick(e));
        window.addEventListener('resize', () => { this.resize(); this.render(); });
    }
    
    // Coordinate transforms
    dateToX(dateStr) {
        const dates = this.getDateRange();
        const idx = dates.indexOf(dateStr);
        if (idx === -1) return null;
        return this.plotLeft + (idx / (dates.length - 1)) * this.plotWidth;
    }
    
    getDateRange() {
        const tracks = this.data.planet_tracks;
        const firstPlanet = this.planetOrder.find(p => tracks[p] && tracks[p].length > 0);
        if (!firstPlanet) return [];
        return tracks[firstPlanet].map(pt => pt.date);
    }
    
    getAllDates() {
        return this.getDateRange();
    }
    
    longitudeToY(lon) {
        // Longitude 0-360 maps to plotHeight (0 at top = 0°, bottom = 360°)
        // But we want zodiac wheel: Aries (0°) at top, moving clockwise down
        // So 0° at top, 360° at bottom
        return this.plotTop + (lon / 360) * this.plotHeight;
    }
    
    yToLongitude(y) {
        return ((y - this.plotTop) / this.plotHeight) * 360;
    }
    
    onMouseMove(e) {
        const rect = this.canvas.getBoundingClientRect();
        const x = (e.clientX - rect.left) * this.dpr;
        const y = (e.clientY - rect.top) * this.dpr;
        
        this.hoveredPoint = this.findNearestPoint(x, y);
        this.render();
        this.updateTooltip(x, y);
    }
    
    onMouseLeave() {
        this.hoveredPoint = null;
        this.render();
        this.hideTooltip();
    }
    
    onClick(e) {
        const rect = this.canvas.getBoundingClientRect();
        const x = (e.clientX - rect.left) * this.dpr;
        const y = (e.clientY - rect.top) * this.dpr;
        
        const point = this.findNearestPoint(x, y);
        if (point) {
            this.selectedPlanet = point.planet;
            this.render();
            this.showPointDetails(point);
        }
    }
    
    findNearestPoint(x, y) {
        const tracks = this.data.planet_tracks;
        let nearest = null;
        let minDist = 20; // pixels
        
        for (const planet of this.planetOrder) {
            const track = tracks[planet];
            if (!track) continue;
            
            for (const pt of track) {
                const px = this.dateToX(pt.date);
                if (px === null) continue;
                const py = this.longitudeToY(pt.longitude);
                
                const dx = px - x;
                const dy = py - y;
                const dist = Math.sqrt(dx*dx + dy*dy);
                
                if (dist < minDist) {
                    minDist = dist;
                    nearest = { ...pt, px, py, planet };
                }
            }
        }
        return nearest;
    }
    
    updateTooltip(x, y) {
        let tooltip = document.getElementById('astro-tooltip');
        if (!tooltip) {
            tooltip = document.createElement('div');
            tooltip.id = 'astro-tooltip';
            tooltip.style.cssText = `
                position: fixed; pointer-events: none; z-index: 1000;
                background: #0f172a; border: 1px solid #1f2c47; border-radius: 8px;
                padding: 10px 12px; font-size: 12px; max-width: 280px;
                box-shadow: 0 8px 24px rgba(0,0,0,.5);
            `;
            document.body.appendChild(tooltip);
        }
        
        if (this.hoveredPoint) {
            const pt = this.hoveredPoint;
            const rect = this.canvas.getBoundingClientRect();
            tooltip.style.left = (rect.left + x / this.dpr + 15) + 'px';
            tooltip.style.top = (rect.top + y / this.dpr - 10) + 'px';
            
            const speedStr = pt.speed >= 0 ? '▲' : '▼';
            const retroStr = pt.retrograde ? ' ☍' : '';
            const combustStr = pt.combust ? ' 🔥' : '';
            
            tooltip.innerHTML = `
                <div style="color:${this.planetColors[pt.planet]};font-weight:700;margin-bottom:4px">
                    ${pt.planet} ${speedStr}${retroStr}${combustStr}
                </div>
                <div style="color:#94a3b8;font-size:11px;line-height:1.6">
                    <div>${pt.sign} ${pt.degree.toFixed(2)}° (${pt.nakshatra} p${pt.pada})</div>
                    <div>House ${pt.house} | Dignity: ${pt.dignity}</div>
                    <div>Speed: ${pt.speed.toFixed(4)}°/day | Strength: ${pt.strength.toFixed(2)}</div>
                    <div>${pt.datetime}</div>
                </div>
            `;
            tooltip.style.display = 'block';
        } else {
            tooltip.style.display = 'none';
        }
    }
    
    hideTooltip() {
        const tooltip = document.getElementById('astro-tooltip');
        if (tooltip) tooltip.style.display = 'none';
    }
    
    showPointDetails(point) {
        // Update side panels with selected planet details
        const eventsPanel = document.getElementById('astro-events');
        if (eventsPanel) {
            const planetEvents = this.data.events.filter(e => e.planet === point.planet);
            eventsPanel.innerHTML = planetEvents.slice(0, 20).map(e => this.renderEventItem(e)).join('');
        }
        
        const aspectsPanel = document.getElementById('astro-aspects');
        if (aspectsPanel) {
            const planetAspects = this.data.aspects.filter(a => a.planet1 === point.planet || a.planet2 === point.planet);
            aspectsPanel.innerHTML = planetAspects.map(a => this.renderAspectItem(a)).join('');
        }
    }
    
    renderEventItem(e) {
        const severityColors = {
            extreme: '#ff0000', strong: '#ff8800', moderate: '#fbbf24', mild: '#7dd3fc'
        };
        const color = severityColors[e.severity] || '#7dd3fc';
        return `
            <div class="astro-event ${e.severity}">
                <div class="astro-event-header">
                    <span class="astro-event-time">${e.datetime.split('T')[1]?.slice(0,5) || ''}</span>
                    <span class="astro-event-type ${e.type}">${e.type}</span>
                </div>
                <div class="astro-event-planet">${e.planet}${e.secondary_planet ? ' / ' + e.secondary_planet : ''}</div>
                <div class="astro-event-desc">${e.description}</div>
            </div>
        `;
    }
    
    renderAspectItem(a) {
        const phaseClass = a.applying ? 'applying' : 'separating';
        const aspectColors = {
            conjunction: '#f87171', opposition: '#f87171', trine: '#34d399',
            square: '#f87171', sextile: '#7dd3fc'
        };
        const color = aspectColors[a.aspect_type] || '#7dd3fc';
        return `
            <div class="astro-aspect ${phaseClass}">
                <div class="astro-aspect-header">
                    <span class="astro-aspect-type ${a.aspect_type}">${a.aspect_type}</span>
                    <span class="astro-aspect-phase ${phaseClass}">${phaseClass}</span>
                </div>
                <div class="astro-aspect-planets">${a.planet1} — ${a.planet2}</div>
                <div class="astro-aspect-dates">Exact: ${a.exact_date} | ${a.start_date} → ${a.end_date}</div>
                <div class="astro-aspect-orb">Orb at exact: ${a.orb_at_exact.toFixed(2)}°</div>
            </div>
        `;
    }
    
    render() {
        const ctx = this.ctx;
        const w = this.width;
        const h = this.height;
        
        // Clear
        ctx.clearRect(0, 0, w, h);
        
        // Background
        ctx.fillStyle = '#0b1120';
        ctx.fillRect(0, 0, w, h);
        
        // Draw nakshatra bands (background)
        if (this.showNakshatras) this.drawNakshatraBands();
        
        // Draw house bands
        if (this.showHouses) this.drawHouseBands();
        
        // Draw retrograde zones
        if (this.showRetrograde) this.drawRetrogradeZones();
        
        // Draw combustion zones
        if (this.showCombustion) this.drawCombustionZones();
        
        // Draw grid lines
        this.drawGrid();
        
        // Draw planet tracks
        this.drawPlanetTracks();
        
        // Draw event markers
        if (this.showEvents) this.drawEventMarkers();
        
        // Draw aspect lines
        if (this.showAspects) this.drawAspectTimelines();
        
        // Draw hovered point highlight
        if (this.hoveredPoint) this.drawHoverHighlight();
        
        // Draw axes and labels
        this.drawAxes();
        
        // Draw legend
        this.drawLegend();
    }
    
    drawNakshatraBands() {
        const ctx = this.ctx;
        const bands = this.data.nakshatra_bands;
        
        for (const band of bands) {
            const y1 = this.longitudeToY(band.start_deg);
            const y2 = this.longitudeToY(band.end_deg);
            
            ctx.fillStyle = band.color + '08'; // Very transparent
            ctx.fillRect(this.plotLeft, y1, this.plotWidth, y2 - y1);
            
            // Nakshatra label on right
            if (band.index % 3 === 0) { // Every 3rd to avoid clutter
                ctx.fillStyle = band.color + '80';
                ctx.font = '9px system-ui';
                ctx.textAlign = 'left';
                ctx.fillText(band.nakshatra.slice(0, 4), this.plotRight + 5, (y1 + y2) / 2 + 3);
            }
        }
    }
    
    drawHouseBands() {
        const ctx = this.ctx;
        const bands = this.data.house_bands;
        
        for (const band of bands) {
            const y1 = this.longitudeToY(band.start_deg);
            const y2 = this.longitudeToY(band.end_deg);
            
            // Alternate subtle shading
            if (band.house % 2 === 0) {
                ctx.fillStyle = '#ffffff05';
                ctx.fillRect(this.plotLeft, y1, this.plotWidth, y2 - y1);
            }
            
            // House number on left
            ctx.fillStyle = '#ffffff30';
            ctx.font = 'bold 11px system-ui';
            ctx.textAlign = 'right';
            ctx.fillText(`H${band.house} ${band.sign}`, this.plotLeft - 8, (y1 + y2) / 2 + 4);
        }
    }
    
    drawRetrogradeZones() {
        const ctx = this.ctx;
        const periods = this.data.retrograde_periods;
        
        for (const period of periods) {
            const x1 = this.dateToX(period.start_date);
            const x2 = this.dateToX(period.end_date);
            if (x1 === null || x2 === null) continue;
            
            const y1 = this.longitudeToY(period.start_deg);
            const y2 = this.longitudeToY(period.end_deg);
            
            // Draw retrograde loop indicator
            ctx.save();
            ctx.beginPath();
            ctx.moveTo(x1, y1);
            ctx.lineTo(x2, y2);
            ctx.strokeStyle = this.planetColors[period.planet] + '60';
            ctx.lineWidth = 3;
            ctx.setLineDash([8, 4]);
            ctx.stroke();
            ctx.restore();
            
            // Label
            ctx.fillStyle = this.planetColors[period.planet] + 'aa';
            ctx.font = 'bold 10px system-ui';
            ctx.textAlign = 'center';
            ctx.fillText(`${period.planet} ☍`, (x1 + x2) / 2, Math.min(y1, y2) - 8);
        }
    }
    
    drawCombustionZones() {
        const ctx = this.ctx;
        const zones = this.data.combustion_zones;
        
        for (const zone of zones) {
            const x1 = this.dateToX(zone.start_date);
            const x2 = this.dateToX(zone.end_date);
            if (x1 === null || x2 === null) continue;
            
            // Combustion is near Sun, so draw at Sun's track
            ctx.fillStyle = '#ff444430';
            ctx.fillRect(x1, this.plotTop, x2 - x1, this.plotHeight);
            
            // Label
            ctx.fillStyle = '#ff4444aa';
            ctx.font = 'bold 10px system-ui';
            ctx.textAlign = 'center';
            ctx.fillText(`🔥 ${zone.planet} combust`, (x1 + x2) / 2, this.plotTop + 20);
        }
    }
    
    drawGrid() {
        const ctx = this.ctx;
        const dates = this.getDateRange();
        
        ctx.strokeStyle = '#1f2c47';
        ctx.lineWidth = 1;
        
        // Vertical date lines
        for (let i = 0; i < dates.length; i += Math.max(1, Math.floor(dates.length / 10))) {
            const x = this.dateToX(dates[i]);
            if (x === null) continue;
            
            ctx.beginPath();
            ctx.moveTo(x, this.plotTop);
            ctx.lineTo(x, this.plotBottom);
            ctx.stroke();
            
            // Date label
            ctx.fillStyle = '#94a3b8';
            ctx.font = '10px system-ui';
            ctx.textAlign = 'center';
            const date = new Date(dates[i]);
            ctx.fillText(`${date.getMonth()+1}/${date.getDate()}`, x, this.plotBottom + 20);
        }
        
        // Horizontal sign lines (every 30°)
        for (let deg = 0; deg <= 360; deg += 30) {
            const y = this.longitudeToY(deg);
            ctx.beginPath();
            ctx.moveTo(this.plotLeft, y);
            ctx.lineTo(this.plotRight, y);
            ctx.stroke();
            
            // Sign label
            const signs = ['Ari', 'Tau', 'Gem', 'Can', 'Leo', 'Vir', 'Lib', 'Sco', 'Sag', 'Cap', 'Aqu', 'Pis'];
            const signIdx = Math.floor(deg / 30) % 12;
            ctx.fillStyle = '#94a3b880';
            ctx.font = '10px system-ui';
            ctx.textAlign = 'right';
            ctx.fillText(signs[signIdx] + ' 0°', this.plotLeft - 8, y + 4);
        }
    }
    
    drawPlanetTracks() {
        const ctx = this.ctx;
        const tracks = this.data.planet_tracks;
        const dates = this.getDateRange();
        
        for (const planet of this.planetOrder) {
            const track = tracks[planet];
            if (!track || track.length < 2) continue;
            
            const color = this.planetColors[planet] || '#888';
            const isSelected = this.selectedPlanet === planet;
            
            ctx.beginPath();
            ctx.strokeStyle = color + (isSelected ? 'ff' : 'cc');
            ctx.lineWidth = isSelected ? 3 : 2;
            ctx.setLineDash([]);
            
            let first = true;
            let wasRetrograde = false;
            
            for (let i = 0; i < track.length; i++) {
                const pt = track[i];
                const x = this.dateToX(pt.date);
                const y = this.longitudeToY(pt.longitude);
                
                if (x === null) continue;
                
                // Handle longitude wrap (360° -> 0°)
                if (!first && i > 0) {
                    const prevPt = track[i-1];
                    const lonDiff = pt.longitude - prevPt.longitude;
                    if (Math.abs(lonDiff) > 180) {
                        // Longitude wrapped - draw discontinuity
                        if (lonDiff > 0) {
                            // Jump from near 360 to near 0 - draw to top then from top
                            ctx.lineTo(x, this.plotTop);
                            ctx.stroke();
                            ctx.beginPath();
                            ctx.moveTo(x, this.plotTop);
                        }
                    }
                }
                
                if (first) {
                    ctx.moveTo(x, y);
                    first = false;
                } else {
                    ctx.lineTo(x, y);
                }
                
                // Change style for retrograde segments
                if (pt.retrograde !== wasRetrograde) {
                    ctx.stroke();
                    ctx.beginPath();
                    ctx.moveTo(x, y);
                    ctx.setLineDash(pt.retrograde ? [6, 4] : []);
                    wasRetrograde = pt.retrograde;
                }
            }
            ctx.stroke();
            
            // Planet label at end
            const lastPt = track[track.length - 1];
            const lastX = this.dateToX(lastPt.date);
            const lastY = this.longitudeToY(lastPt.longitude);
            if (lastX !== null) {
                ctx.fillStyle = color;
                ctx.font = 'bold 11px system-ui';
                ctx.textAlign = 'left';
                const symbol = {
                    "Sun": "☉", "Moon": "☽", "Mars": "♂", "Mercury": "☿",
                    "Jupiter": "♃", "Venus": "♀", "Saturn": "♄", "Rahu": "☊", "Ketu": "☋"
                }[planet] || planet[0];
                ctx.fillText(`${symbol} ${planet}`, lastX + 5, lastY + 4);
            }
        }
    }
    
    drawEventMarkers() {
        const ctx = this.ctx;
        const events = this.data.events;
        
        for (const event of events) {
            const x = this.dateToX(event.date);
            if (x === null) continue;
            
            const severityColors = {
                extreme: '#ff0000', strong: '#ff8800', moderate: '#fbbf24', mild: '#7dd3fc'
            };
            const color = severityColors[event.severity] || '#7dd3fc';
            
            // Event marker on timeline
            ctx.beginPath();
            ctx.arc(x, this.plotBottom + 10, 4, 0, Math.PI * 2);
            ctx.fillStyle = color;
            ctx.fill();
            ctx.strokeStyle = '#0b1120';
            ctx.lineWidth = 1;
            ctx.stroke();
            
            // Event type icon
            const icons = {
                ingress: '▶', retrograde_start: '☍', retrograde_end: '☋',
                station: '■', combustion_start: '🔥', combustion_end: '✦',
                nakshatra_change: '◆', eclipse: '☀', aspect_exact: '✶'
            };
            ctx.fillStyle = '#ffffff';
            ctx.font = '10px system-ui';
            ctx.textAlign = 'center';
            ctx.fillText(icons[event.type] || '•', x, this.plotBottom + 22);
        }
    }
    
    drawAspectTimelines() {
        const ctx = this.ctx;
        const aspects = this.data.aspects;
        
        for (const aspect of aspects) {
            const x1 = this.dateToX(aspect.start_date);
            const x2 = this.dateToX(aspect.end_date);
            if (x1 === null || x2 === null) continue;
            
            const exactX = this.dateToX(aspect.exact_date);
            
            const aspectColors = {
                conjunction: '#f87171', opposition: '#f87171', trine: '#34d399',
                square: '#f87171', sextile: '#7dd3fc'
            };
            const color = aspectColors[aspect.aspect_type] || '#7dd3fc';
            
            // Aspect timeline bar at bottom
            const y = this.plotBottom + 35;
            
            ctx.beginPath();
            ctx.moveTo(x1, y);
            ctx.lineTo(x2, y);
            ctx.strokeStyle = color + (aspect.applying ? 'ff' : '80');
            ctx.lineWidth = 4;
            ctx.lineCap = 'round';
            ctx.stroke();
            
            // Exact point
            if (exactX !== null) {
                ctx.beginPath();
                ctx.arc(exactX, y, 3, 0, Math.PI * 2);
                ctx.fillStyle = color;
                ctx.fill();
            }
            
            // Label
            ctx.fillStyle = color;
            ctx.font = '9px system-ui';
            ctx.textAlign = 'center';
            const label = `${aspect.planet1[0]}${aspect.aspect_type[0]}${aspect.planet2[0]}`;
            ctx.fillText(label, (x1 + x2) / 2, y - 8);
        }
    }
    
    drawHoverHighlight() {
        const ctx = this.ctx;
        const pt = this.hoveredPoint;
        if (!pt) return;
        
        // Crosshair
        ctx.strokeStyle = '#fbbf2480';
        ctx.lineWidth = 1;
        ctx.setLineDash([4, 4]);
        
        ctx.beginPath();
        ctx.moveTo(pt.px, this.plotTop);
        ctx.lineTo(pt.px, this.plotBottom);
        ctx.stroke();
        
        ctx.beginPath();
        ctx.moveTo(this.plotLeft, pt.py);
        ctx.lineTo(this.plotRight, pt.py);
        ctx.stroke();
        
        // Point highlight
        ctx.beginPath();
        ctx.arc(pt.px, pt.py, 8, 0, Math.PI * 2);
        ctx.strokeStyle = this.planetColors[pt.planet];
        ctx.lineWidth = 2;
        ctx.setLineDash([]);
        ctx.stroke();
        
        ctx.setLineDash([]);
    }
    
    drawAxes() {
        const ctx = this.ctx;
        
        // Y-axis (longitude)
        ctx.strokeStyle = '#1f2c47';
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(this.plotLeft, this.plotTop);
        ctx.lineTo(this.plotLeft, this.plotBottom);
        ctx.stroke();
        
        // Longitude labels
        ctx.fillStyle = '#94a3b8';
        ctx.font = '9px system-ui';
        ctx.textAlign = 'right';
        for (let deg = 0; deg <= 360; deg += 30) {
            const y = this.longitudeToY(deg);
            ctx.fillText(`${deg}°`, this.plotLeft - 10, y + 3);
        }
        
        // X-axis label
        ctx.fillStyle = '#94a3b8';
        ctx.font = '11px system-ui';
        ctx.textAlign = 'center';
        ctx.fillText('Date', this.width / 2, this.height - 10);
        
        // Y-axis label (vertical)
        ctx.save();
        ctx.translate(30, this.height / 2);
        ctx.rotate(-Math.PI / 2);
        ctx.fillText('Sidereal Longitude (0° Aries at top)', 0, 0);
        ctx.restore();
    }
    
    drawLegend() {
        const ctx = this.ctx;
        const x = this.plotRight - 10;
        let y = this.plotTop;
        
        ctx.font = '10px system-ui';
        ctx.textAlign = 'right';
        
        for (const planet of this.planetOrder) {
            const color = this.planetColors[planet];
            const isSelected = this.selectedPlanet === planet;
            
            // Color dot
            ctx.beginPath();
            ctx.arc(x - 8, y + 5, 4, 0, Math.PI * 2);
            ctx.fillStyle = color + (isSelected ? 'ff' : 'cc');
            ctx.fill();
            if (isSelected) {
                ctx.strokeStyle = '#fbbf24';
                ctx.lineWidth = 2;
                ctx.stroke();
            }
            
            // Label
            ctx.fillStyle = isSelected ? '#fbbf24' : '#e2e8f0';
            ctx.fillText(planet, x - 14, y + 9);
            y += 18;
        }
    }
}

// Initialize from API data
async function loadAstroPlot(date, windowDays, resolution, houseSystem) {
    const params = new URLSearchParams({
        date: date,
        window: windowDays,
        resolution: resolution,
        house_system: houseSystem
    });
    
    try {
        const resp = await fetch(`/api/astro_plot?${params}`);
        if (!resp.ok) throw new Error('Failed to load');
        const data = await resp.json();
        
        // Create chart
        window.astroChart = new AstroPlotChart('astro-track-chart', data);
        
        // Update subtitle
        const sub = document.getElementById('astro-plot-sub');
        if (sub) {
            sub.textContent = `${data.start_date} → ${data.end_date} · ${data.resolution} · ${data.planet_tracks.Sun.length} points · ${data.events.length} events · ${data.aspects.length} aspects`;
        }
        
        // Populate events panel (all events initially)
        const eventsPanel = document.getElementById('astro-events');
        if (eventsPanel) {
            eventsPanel.innerHTML = data.events.slice(0, 30).map(e => renderEventItemStatic(e)).join('');
        }
        
        // Populate aspects panel
        const aspectsPanel = document.getElementById('astro-aspects');
        if (aspectsPanel) {
            aspectsPanel.innerHTML = data.aspects.slice(0, 20).map(a => renderAspectItemStatic(a)).join('');
        }
        
    } catch (err) {
        console.error('Astro plot load failed:', err);
    }
}

// Static renderers for initial load
function renderEventItemStatic(e) {
    const severityColors = { extreme: '#ff0000', strong: '#ff8800', moderate: '#fbbf24', mild: '#7dd3fc' };
    const color = severityColors[e.severity] || '#7dd3fc';
    return `
        <div class="astro-event ${e.severity}">
            <div class="astro-event-header">
                <span class="astro-event-time">${e.datetime.split('T')[1]?.slice(0,5) || ''}</span>
                <span class="astro-event-type ${e.type}">${e.type}</span>
            </div>
            <div class="astro-event-planet">${e.planet}${e.secondary_planet ? ' / ' + e.secondary_planet : ''}</div>
            <div class="astro-event-desc">${e.description}</div>
        </div>
    `;
}

function renderAspectItemStatic(a) {
    const phaseClass = a.applying ? 'applying' : 'separating';
    return `
        <div class="astro-aspect ${phaseClass}">
            <div class="astro-aspect-header">
                <span class="astro-aspect-type ${a.aspect_type}">${a.aspect_type}</span>
                <span class="astro-aspect-phase ${phaseClass}">${phaseClass}</span>
            </div>
            <div class="astro-aspect-planets">${a.planet1} — ${a.planet2}</div>
            <div class="astro-aspect-dates">Exact: ${a.exact_date} | ${a.start_date} → ${a.end_date}</div>
            <div class="astro-aspect-orb">Orb at exact: ${a.orb_at_exact.toFixed(2)}°</div>
        </div>
    `;
}

// Auto-init when panel is visible
document.addEventListener('DOMContentLoaded', () => {
    // Check if astro plot panel exists
    const panel = document.querySelector('.astro-plot-panel');
    if (panel) {
        // Get current date from main date input
        const dateInput = document.getElementById('date');
        const date = dateInput ? dateInput.value : new Date().toISOString().split('T')[0];
        
        const windowSel = document.getElementById('astro-window');
        const resSel = document.getElementById('astro-resolution');
        const houseSel = document.getElementById('astro-house');
        const refreshBtn = document.getElementById('astro-refresh');
        
        const load = () => loadAstroPlot(
            date,
            parseInt(windowSel?.value || '30'),
            resSel?.value || 'daily',
            houseSel?.value || 'whole_sign'
        );
        
        windowSel?.addEventListener('change', load);
        resSel?.addEventListener('change', load);
        houseSel?.addEventListener('change', load);
        refreshBtn?.addEventListener('click', load);
        
        // Also reload when main date changes
        dateInput?.addEventListener('change', () => {
            loadAstroPlot(dateInput.value, parseInt(windowSel.value), resSel.value, houseSel.value);
        });
        
        // Initial load
        load();
    }
});