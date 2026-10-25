# SBC Tool: Historical Pattern Hypothesis Workstation

A Flask research workstation that tests a hypothesis: do planetary cycles, computed from Swiss Ephemeris orbital data, carry information about NIFTY market moves? The cycle features come from a traditional 81-cell timing model, the **Sarvatobhadra Chakra (SBC)**, and every signal is tested out of sample against market controls.

## Features

> **Research tool, not investment advice.** Every planetary-cycle signal here has been tested
> out of sample against NIFTY (rules, analogs, factors, sectors, swing entries) and
> none has shown an edge so far. The forecast card stays at the base rate unless a
> component passes both the permutation test and the incremental test against market
> controls. Reports: `docs/research/`; running tally: `docs/GAP_ANALYSIS_PREDICTION_ENGINE_2026-10-03.md`.

### Core planetary-cycle engine
- **81-cell Sarvatobhadra Chakra** with 28 nakshatras, 16 vowels, 20 consonants, 12 rashis, 5 tithi groups
- **Two vedha schools**: Classical (single ray) and All-three rays (Narasimha Rao); KP is used for the intraday layer, not for vedha
- **Lahiri ayanamsa** with Swiss Ephemeris (Moshier); KP ayanamsa and Placidus cusps for the KP data files
- **Market anchors**: NSE, BSE, NIFTY 50, SENSEX, India national market
- **NSE holiday calendar** (2024–2026, special closures, Muhurat) used by forecasts, the ledger and KP generation

### Workspaces (tabs)
| Tab | What it shows |
|-----|---------------|
| **Executive Overview** | Next-session NIFTY forecast card (probability, VIX bands, evidence with verdicts), crash/volatility risk, reversal watch, the interactive SBC Chakra with birth-data profiles, Bhadra calendar, weekly confluence commentary, Rahu/Ketu trap calendar, yoga alerts, trading signals from live tithi/Bhadra/reversal windows |
| **Chart & Timing** | NIFTY 50 planetary-cycle price chart (prediction overlay, crash score, Gann zones and Gann initiation/target/SL markers), intraday cycle projection, AstroCycle Pro Mercury/Moon bars, expiry range indicator, crash and bullish futurecasts |
| **Sector Heatmap** | SBC sector dashboard, monthly sector confluence heatmap, sector vedha radar, bullion and transit vedha matrices, large-cap divergence (CGSP), FMCG/tourism/chemical/alcohol sector signals, lunar cycle sector forecast, daily nakshatra confluence |
| **Research Lab** | Event studies, walk-forward validation, planetary aspect grid, solar/lunar cycles |
| **KP Intraday** | SBC + KP intraday forecast, KP trend-change report (DOCX export) and intraday path — all labelled *experimental, no validated edge*; Kota Chakra prediction |
| **Monthly Projection** | Daily indication balance (Jyotish/KP/Western blend) and confluence calendar matrix |
| **Analog Lab** | Tiered sky-similarity analogs with forward-return distributions |
| **Forward Calendar** | Next weeks' planetary events with the frozen forecast for each session (also as weekly HTML/Markdown reports) |
| **Swing Windows** | Heliocentric Earth–planet aspect windows as entries, Gann + Fibonacci + indicator confluence as exits; TradingView Pine script in `tools/tradingview/` |

### API-only
- Routes with no panel are kept only when something else uses them: `/healthz` (Docker), `/webhook/sbc` and `/api/sbc/latest` (TradingView alerts), `/api/engine/aspect_windows?format=tv` (the Pine script), and the engine's operational endpoints (fingerprint status, forecast ledger, intraday freeze/score, market freshness, version). `tests/test_route_pruning.py` fails if a new route has neither a UI caller nor a place on that list.
- **Live forecast ledger** freezes each session's forecast before the open and scores it after the close (`scripts/forecast_ledger.py`, run by `run_app.py`).

## Quick Start

### Prerequisites
- Python 3.11+
- pip / uv

### Installation

```bash
# Clone and enter directory
cd SBC_Tool

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Or with uv (faster)
uv pip install -r requirements.txt

# City search for birth data: ~34k GeoNames cities (downloads ~3.5 MB once)
python scripts/seed_cities.py
```

City data © [GeoNames](https://www.geonames.org/), CC BY 4.0.

### Run Development Server

```bash
# Run (port 8000; warms the chart cache and runs the forecast ledger in the background)
python run_app.py
python run_app.py --host 127.0.0.1 --port 8000 --debug   # dev options; --no-warm, --no-ledger

# Bare server without the background jobs (127.0.0.1:8000)
python app.py

# Or with gunicorn (production-like)
gunicorn -w 4 -b 0.0.0.0:8000 app:app
```

### Write access (profiles, habits, webhook)

Every non-GET endpoint mutates state. By default writes are accepted from
**localhost only**, so binding to `0.0.0.0` for a phone on the LAN does not
let that phone rewrite data. To allow remote writes, set a shared secret:

```bash
export SBC_API_TOKEN="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
```

Clients then send it as `X-API-Token`. In the browser, store it once and the
UI attaches it to every write automatically:

```js
localStorage.setItem('sbcApiToken', '<token>')
```

The Kota Chakra workbook is read from `data/kota/Prediction_Kota_Chakra*.xlsx`
(newest wins) or the path in `SBC_KOTA_XLSX`.

Open http://localhost:8000 in your browser.

## Architecture

```
SBC_Tool/
├── app.py                 # Flask application factory & routes
├── requirements.txt       # Python dependencies
├── pyproject.toml         # Project config (ruff, mypy, pytest)
├── sbc/                   # Core planetary-cycle engine
│   ├── __init__.py
│   ├── chakra.py          # 81-cell grid definition
│   ├── planets.py         # Planetary positions (Swiss Ephemeris)
│   ├── nakshatra.py       # Nakshatra, tithi, paksha calculations
│   ├── prediction.py      # Vedha computation, analysis, recommendation
│   ├── market_calendar.py # Reversal alerts, yoga alerts
│   ├── backtest.py        # Historical backtesting engine
│   ├── trade_setups.py    # Trade setup definitions
│   ├── sector_signals.py  # Plantation/fertilizer vedha signals
│   ├── monthly_heatmap.py # Sector × day confluence matrix
│   ├── intraday_projection.py # Hourly NIFTY cycle projection
│   ├── weekly_commentary.py   # Weekly synthesis
│   ├── lunar_forecast.py      # Lunar cycle sector forecast
│   ├── bullion_vedha.py       # Gold/Silver vedha matrix
│   ├── transit_vedha.py       # Sector transit triggers
│   ├── fmcg_signals.py        # FMCG planetary syntax
│   ├── tourism_signals.py     # Tourism/leisure signals
│   ├── chemical_signals.py    # Chemical sector signals
│   ├── alcohol_signals.py     # Alcohol sector signals
│   ├── cgsp_framework.py      # Cruel-Gentle Sign-Pada
│   ├── kp_intraday.py         # KP intraday trend changes
│   ├── kp_config.py           # KP configuration
│   ├── kota_chakra.py         # Kota chakra predictions
│   ├── bhadra.py              # Bhadra (Vishti Karana) calendar
│   ├── astro_plot.py          # Planetary-cycle chart plotting
│   ├── config.py              # Rashi-sector mappings, constants
│   ├── metrics.py             # Bias scaling, western bias
│   ├── market_data.py         # NIFTY OHLC, moon rashi
│   ├── confluence.py          # Multi-factor confluence
│   ├── db.py                  # SQLite schema & bootstrap
│   ├── navamsa_pipeline/      # Navamsa/KP data pipeline
│   └── api/                   # API blueprints (engine, sector)
├── templates/
│   └── index.html         # Main SPA template
├── static/
│   ├── app.js             # Main SPA logic
│   ├── nifty-chart.js     # Lightweight-charts price overlay
│   ├── intraday-projection.js
│   ├── astro-plot.js
│   ├── style.css          # All styling
│   ├── chart.umd.min.js   # Chart.js (for KP path)
│   └── vendor/lightweight-charts.js
├── data/
│   ├── profiles.db        # SQLite for user profiles/habits
│   ├── schema.sql         # Database schema
│   ├── kp/                # KP CSV data files
│   └── output/            # Backtest CSV outputs
├── scripts/               # Test & utility scripts
└── tests/                 # Pytest test suite (to be created)
```

## API Reference

### Core Prediction
```
GET  /api/prediction?date=YYYY-MM-DD&time=HH:MM&tz=Asia/Kolkata&anchor=nse&school=allthree
GET  /api/presets                    # Available anchors, nakshatras
GET  /api/prediction_series?start=...&end=...&anchor=nifty&school=allthree
GET  /api/daily_indication_balance?start=YYYY-MM-DD&anchor=nifty
GET  /api/daily_confluence?date=YYYY-MM-DD&days=7
```

### Charting
```
GET  /api/nifty_chart?start=...&end=...
GET  /api/nakshatra_chart?date=...&months=3
GET  /api/intraday_projection?date=...&tz=...&anchor=...&days=5
GET  /api/astro_plot?date=...&window=30&resolution=daily&tz=...&lat=...&lon=...
```

### Backtesting & Futurecast
```
GET  /api/backtest
GET  /api/futurecast?date=...
GET  /api/bullish_futurecast?date=...&years=1
GET  /api/crash_score_series?start=...&end=...
```

### Sector & Specialized Signals
```
GET  /api/sector_vedha?date=...
GET  /api/monthly_heatmap?date=...&days=30&anchor=nse
GET  /api/bullion_vedha?date=...          (daily)
GET  /api/bullion_vedha_week?date=...     (weekly)
GET  /api/transit_vedha?date=...          (daily)
GET  /api/transit_vedha_week?date=...     (weekly)
GET  /api/fmcg_signals?date=...&price=...
GET  /api/tourism_signals?date=...&price=...
GET  /api/chemical_signals?date=...&price=...
GET  /api/alcohol_signals?date=...&price=...
GET  /api/largecap_divergence?date=...
GET  /api/lunar_forecast?date=...
GET  /api/bhadra_calendar?date=...&offset=0
GET  /api/weekly_commentary?date=...
```

### KP Intraday
```
GET  /api/kp_intraday_report?date=...&instrument=NIFTY&format=json
POST /api/kp_intraday_sample  {date, days}
GET  /api/engine/intraday_path?date=...&instrument=NIFTY
```

### Research Lab
```
GET  /api/research/event-study?...
GET  /api/research/walk-forward?...
GET  /api/research/aspects?...
GET  /api/research/cycles?start=...&end=...
```

### Market data (prediction engine)
```
GET  /api/engine/market/freshness
GET  /api/engine/fingerprint?date=YYYY-MM-DD[&vector=1]
GET  /api/engine/fingerprint/status
GET  /api/engine/analogs?date=&horizon=1|5|20&variant=overall|slow|medium|fast&k=30
GET  /api/engine/forecast?date=&horizon=1|5|20
GET  /api/engine/forecast/ledger?horizon=1|5|20&kind=live|late|backfill
GET  /api/engine/forecast/card?date=
GET  /api/engine/calendar?start=&weeks=1..8&format=json|html|md
GET  /api/engine/calendar/reports
GET  /api/engine/calendar/reports/<file>
GET  /api/engine/aspect_windows?start=&end=&planet=&aspect=&format=json|tv
GET  /api/engine/swing_windows?start=&end=&planet=&aspect=&confluence=3|2
```
`data/market.db` holds NIFTY, SENSEX and India VIX daily bars (yfinance) and NSE
FII/DII cash flows. `run_app.py` refreshes it after each close; the first backfill is
`python scripts/refresh_market_data.py --full`. NSE serves FII/DII for the latest
session only, so that series grows one day at a time.

`data/fingerprints.db` holds the planetary fingerprint (every planet, aspect,
panchang, KP and SBC factor at 09:15 IST) for each day 1990–2035. Build or
refresh it with `python scripts/build_fingerprints.py` (about 15 s). Rows are
versioned by the engine code, so an engine change triggers a rebuild of the stale days.

The **Analog Lab** tab (Advanced analysis) finds past NIFTY sessions with the most similar
sky and shows what followed them, next to the engine's walk-forward track record.
`python scripts/validate_rules.py` and `python scripts/validate_analogs.py` regenerate
the validation reports in `docs/research/`, and `python scripts/validate_incremental.py`
tests whether any planetary-cycle signal adds information beyond market controls (VIX, trend,
volatility, calendar). None has so far; treat every output as research, not advice.

New candidate factors (stations, combustion, planetary war, out-of-bounds declination,
ingress and eclipse days, retrograde clusters, Moon–node contacts, Jupiter's dignity) live
in `sbc/factors.py` with their direction fixed in advance; `python scripts/validate_factors.py`
grades them, and one counts in the forecast only after passing both tests. The sector
vedha scenarios are tested on the years before the window they were picked on:
`python scripts/refresh_market_data.py --research --full` downloads the commodity and
sector-stock series, then `python scripts/validate_sectors.py` writes the report.

The **Swing Windows** tab (B-39) marks heliocentric Earth–planet aspect windows as ENTRY
zones and exits on Gann + Fibonacci + indicator confluence (`sbc/helio_aspects.py`,
`sbc/swing_model.py`). `/api/engine/aspect_windows?format=tv` returns the
`{dates, label, skip_holidays}` payload for the TradingView indicator in
`tools/tradingview/astro_swing_windows.pine`. `python scripts/validate_swing.py` compares
the entries with random dates and the exit with simple exits. So far the model does no
better than either.

`/api/engine/forecast` combines all of it into one NIFTY forecast per session and
horizon. Its probability stays at the historical base rate until a component passes
both tests. `run_app.py` freezes it before each open into `data/daily_ledger.db` and
scores it once the outcome is in, building a live track record.

The Executive Overview opens with the forecast **evidence card**
(`/api/engine/forecast/card`): the next session's 1/5/20-session chance of a rise, the
VIX-implied range, the live record, and every rule's lean next to its test results. The
**Forward Calendar** tab (Advanced analysis) lays out the coming weeks: weekly range,
sky events (ingresses, stations, exact aspects, eclipses, new/full Moon) and each day's
rule and analog leans. `run_app.py` writes a copy to `reports/calendar/` every Saturday
from 08:00 IST; without the server, run `python scripts/forward_calendar.py --weekly`
from Windows Task Scheduler.

### Profile Management
```
GET    /api/astro/profile?user_key=...
POST   /api/astro/profile              {data}
PUT    /api/astro/profile/<id>         {name}
POST   /api/astro/profile/<id>/default
DELETE /api/astro/profile/<id>
GET    /api/astro/profile/export?user_key=...
POST   /api/astro/profile/import       [{data, name, is_default}]
```

### Utilities
```
GET  /api/tz/offset?tz=...&date=...&time=...
GET  /api/tz/from_coords?lat=...&lon=...
GET  /api/price?ticker=^NSEI&days=180
GET  /api/cities/search?q=...&country=...&limit=20   # GeoNames, best match first
GET  /api/gann/precision?ticker=...&days=90
GET  /api/signal/moon?ticker=...&days=30
GET  /api/backtest/walkforward?ticker=...&window=365&step=90
POST /api/habits/log     {habit_type, date}
GET  /api/habits/streaks?user_key=...
GET  /api/habits/history?user_key=...&days=7
POST /webhook/sbc        {signal_data}
GET  /api/sbc/latest
```

## Development

### Code Quality

```bash
# Lint + import order (the same command CI runs; rules in pyproject.toml)
ruff check sbc/ app.py run_app.py scripts/ tests/

# Type check (blocking in CI)
mypy sbc/ app.py --ignore-missing-imports
```

### Testing

```bash
# Run all tests with coverage
pytest --cov=sbc --cov-report=html

# Run specific test file
pytest tests/test_prediction.py -v

# Run with keyword filter
pytest -k "backtest" -v
```

### Project Structure for Tests

```
tests/
├── conftest.py              # Fixtures
├── test_planets.py          # Planetary position tests
├── test_nakshatra.py        # Tithi, nakshatra, paksha tests
├── test_chakra.py           # Grid, vedha computation tests
├── test_prediction.py       # Analysis, recommendation tests
├── test_backtest.py         # Backtest engine tests
├── test_kp_intraday.py      # KP intraday tests
├── test_api.py              # Flask API endpoint tests
└── test_integration.py      # End-to-end integration tests
```

## Configuration

### Environment Variables
```bash
FLASK_APP=app.py
FLASK_DEBUG=1
FLASK_ENV=development
SECRET_KEY=your-secret-key  # For production
DATABASE_URL=sqlite:///data/profiles.db  # Default
```

### Market Anchors (sbc/engine.py)
Modify `ANCHORS` dict to add custom market birth dates:
```python
ANCHORS = {
    "nse": {"name": "NSE", "date": "1992-11-27", "time": "00:00", "tz": "Asia/Kolkata"},
    "custom": {"name": "My Market", "date": "2000-01-01", "time": "09:15", "tz": "Asia/Kolkata"},
}
```

### Sector Mappings (sbc/config.py)
```python
SECTOR_NAME_MAP = {
    "Aries": ["Defence", "Engineering"],
    "Taurus": ["Banking", "Finance"],
    # ... add custom mappings
}
```

## Deployment

### Docker

```dockerfile
# Dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:8000", "app:app"]
```

```bash
docker build -t sbc-tool .
docker run -p 8000:8000 sbc-tool
```

### Docker Compose

```yaml
# docker-compose.yml
version: '3.8'
services:
  app:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/data
    environment:
      - FLASK_ENV=production
    restart: unless-stopped
```

### Production Checklist
- [ ] Set `FLASK_ENV=production`
- [ ] Set strong `SECRET_KEY`
- [ ] Use `gunicorn` with multiple workers
- [ ] Configure reverse proxy (nginx)
- [ ] Enable HTTPS
- [ ] Set up Redis for rate limiting cache
- [ ] Configure logging (structlog + file rotation)
- [ ] Set up monitoring (Sentry, Prometheus)

## Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature/amazing-feature`
3. Run code quality checks: `ruff check sbc/ app.py run_app.py scripts/ tests/`
4. Write tests for new functionality
5. Ensure all tests pass: `pytest`
6. Commit with conventional commits: `feat: add amazing feature`
7. Push and create Pull Request

## License

MIT License - see LICENSE file for details.

## Disclaimer

**This software is for educational and research purposes only. It does not constitute financial advice, solicitation, or recommendation to buy or sell any securities or derivatives. Financial markets involve substantial risk of loss. Trade on your own analysis and risk management.**

## Acknowledgments

- **Swiss Ephemeris** (Moshier) for high-precision planetary positions
- **Lahiri Ayanamsa** for sidereal zodiac calculations
- **TradingView Lightweight Charts** (MIT) for price charting
- **Chart.js** (MIT) for KP intraday path visualization
- Classical texts: Phaladeepika, Horaratna, Narapatijayacharya

---

**A research project in testing historical market-pattern hypotheses with out-of-sample statistics.**