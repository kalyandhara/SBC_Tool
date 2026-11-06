# AstroTrade Navigator: Phase 1 Design

Date: 2026-11-06. Session bead: SBC_Tool-me7. Status: design approved by the user, spec awaiting review.

## Goal

A natal-chart decision-support and research feature that behaves like a quantitative model and can be tested. Phase 1 delivers one natal chart, a daily 0-100 score with additive lineage, and a walk-forward Nifty backtest, verified in the running app.

## Agreed decisions

| Decision | Choice | Consequence |
|---|---|---|
| App home | Extend the Flask app | FastAPI and React are dropped from the original stack. API is a Flask blueprint; UI is a plain JS tab. |
| Database | Postgres in Docker | Docker Desktop must be running to build or verify. |
| Natal data | Clearly marked sample | Real data is entered locally in the app by the user, never via chat or git. |
| Planet Strength | Partial index, labelled | Shadbala and Avastha arrive in Phase 2. |

## Components

- `sbc/navigator/scoring.py`: pure functions. Six terms, combination, bands, action mapping.
- `sbc/navigator/weights.py`: hand-set weight tables, with a version string.
- `sbc/navigator/lineage.py`: builds the factor list for a day.
- `sbc/navigator/backtest.py`: folds, band statistics, controls, placebo charts.
- `sbc/navigator/store.py`: only module that touches Postgres.
- `sbc/yogas.py`: `vimshottari` gains Pratyantar as a third level, without changing existing keys.
- `sbc/api/blueprints/navigator_bp.py`: routes, registered the way other blueprints are.
- `static/js/navigator.js`, `templates/index.html`, `static/style.css`: the Navigator tab. No new CDN dependency.
- `docker-compose.yml`: `postgres` service, port bound to `127.0.0.1`, password from the environment, named volume.

The scoring and backtest modules take plain inputs and do not import the store, so they are testable without Postgres.

## Schema

```sql
natal_profile(id PK, label TEXT, is_sample BOOL NOT NULL, birth_date DATE, birth_time TIME,
              tz TEXT, lat DOUBLE PRECISION, lon DOUBLE PRECISION, created_at TIMESTAMPTZ)
daily_score(profile_id FK, day DATE, weights_version TEXT, data_asof DATE, engine_version TEXT, chart_hash TEXT,
            score NUMERIC, band TEXT, action TEXT, lineage JSONB,
            PRIMARY KEY(profile_id, day, weights_version, data_asof, engine_version, chart_hash))
backtest_run(id PK, profile_id FK, instrument TEXT, weights_version TEXT, data_asof DATE, engine_version TEXT, chart_hash TEXT, status TEXT NOT NULL, heartbeat_at TIMESTAMPTZ, error TEXT, params JSONB,
             folds JSONB, results JSONB, created_at TIMESTAMPTZ)
```

`tz` is an IANA name. Future-dated scores are never cached. A stored row is reused only if all key fields match. Prices remain in `data/market.db` and are not copied. Migrations are plain numbered SQL files in `sbc/navigator/migrations/`.

## Endpoints

- `GET /api/navigator/profile`, `POST /api/navigator/profile` (POST follows the existing `SBC_API_TOKEN` rule for non-local callers)
- `GET /api/navigator/chart?profile_id=`
- `GET /api/navigator/score?profile_id=&day=` returns score, band, action, lineage
- `POST /api/navigator/backtest` and `GET /api/navigator/backtest/<id>`

The run takes longer than a request should block, so POST starts a background thread and GET reports status and results. Run state lives in `backtest_run` (`status` queued/running/done/failed, `heartbeat_at`), never in worker memory. One active run per profile: a repeat POST returns the existing run. A run with a stale heartbeat is marked failed. A failed run stores its error and the page shows it. If Postgres is down, routes return 503 with a clear message and the rest of the app keeps working: the navigator module must not make app start-up depend on Postgres.

A `before_request` guard covers the whole blueprint, reads included: `X-API-Token` when `SBC_API_TOKEN` is set, otherwise direct local callers only. A caller with proxy headers such as `X-Forwarded-For` and no token is refused. The Postgres password comes from a gitignored `.env`, is required, and has no default.

Birth data is never logged, and profile fields never appear in URLs beyond the numeric id. **Accepted risk (user-approved):** `natal_profile` is not encrypted at rest in Phase 1.

Profile input is validated: exact birth time, valid latitude, longitude and IANA timezone. Invalid input is rejected, never defaulted. A new `lagna_at(date, time, tz, lat, lon)` takes coordinates directly with no city fallback, and lagna is a natal point for aspects. The score does not depend on houses in Phase 1.

## Scoring

Each term is 0-100.

```
Score = .25 Transit + .20 Moon + .20 Dasha + .15 Strength + .10 HistVal + .10 Vol
```

- **Transit**: sum over active Sun-to-Ketu aspects (conjunction, opposition, square, trine, sextile) to natal points of `weight × orb_factor`, where `orb_factor` falls linearly from 1 at exact to 0 at the orb edge. Raw sum clipped to ±100, then `(raw + 100) / 2`. User-specified examples: Jupiter trine natal Jupiter +40, Mars square natal Mercury -20, Saturn opposite Moon -35.
- **Moon**: sign, nakshatra, tithi and phase points give a -100 to +100 Moon Sentiment Score, shown as is, then `(raw + 100) / 2`.
- **Dasha**: lord favourability for Mahadasha, Antardasha and Pratyantar, weighted 50/30/20.
- **Strength** (partial, labelled "no Shadbala/Avastha yet"): dignity, combustion and retrograde for the planets active that day.
- **HistVal**: for the score's band, the past-only excess return rank mapped to 0-100. A past session counts only once its full return horizon has closed before the entry point (an embargo of `horizon` sessions). Neutral 50 for the first 3 years. To avoid circularity it is computed from the other five terms' score.
- **Vol**: 100 minus the trailing 252-session India VIX percentile, as of the T-1 close, from the `INDIAVIX` series. Neutral 50 on future dates or missing data, flagged in lineage. `data/vix_ohlc.csv` is not used.

**Lineage**: each factor has `term, label, raw, weight, contribution`. Contributions are rounded to fixed precision with the residual placed on the largest factor, so displayed values sum exactly to the displayed score. Text uses weighted-factor language only.

**Bands**: 0-20 No Trading, 21-40 Very Defensive, 41-60 Normal, 61-80 High Probability, 81-100 Exceptional Setup. Scores are rounded to integers before banding.

**Actions**: Exceptional Setup → Trade Aggressively, High Probability → Trade Normally, Normal → Reduce Position Size, Very Defensive → Stay Cash, No Trading → Avoid Market Entirely. The band-to-action mapping is a choice made here, as the brief does not specify it. Labels are always shown as unvalidated research output with a disclaimer, never as personal advice.

Weight tables are written before any returns are examined and are never fitted. Any later change after seeing results bumps `weights_version` and is disclosed as in-sample.

## Backtest

- Instrument: Nifty, 2007 onward. Entry at day T's open, with the T-1 close as the last input, for all terms. Returns are measured open-to-close and open-to-open, so overnight gaps count.
- Walk-forward: expanding train window, yearly test folds. Train windows supply HistVal only. Nothing else is fitted.
- Metrics per band: daily and weekly return, volatility, drawdown, hit rate, win rate, Sharpe-like score, net of 10 bps round trip (a parameter).
- Controls: decile-matched same-day controls (sessions outside the band, matched on the decile of the T-1 session's return), and 200 random placebo birth charts on a fixed seed.
- Placebos: birth moments uniform over 1950-2005 with random locations. Each runs the identical walk-forward pipeline, HistVal included. The real chart's placebo percentile is reported for the full score and for a natal-only sub-score (Transit, Dasha, Strength), since Moon and Vol are common to all charts. Daily planet positions are computed once and shared. A 200-chart run must finish within 10 minutes; if it cannot, the count is reduced and disclosed on the page.
- Occupancy: days and events per band are reported. Bands are not rescaled. If the extreme bands are empty, that goes to the user as a decision, and any rescaling must use past data only and take a new `weights_version`.
- Events: consecutive days in a band collapse to one event. Event counts are reported beside day counts, and bands below the minimum event count show "insufficient events".
- Multiple testing: Benjamini-Hochberg across bands and horizons. Permutation tests use the circular shift in `sbc/stats.py`.
- Results pinned by a frozen fixture for determinism.
- Verdict, fixed in code before results: "edge candidate" only if BH q < 0.10 net of costs, the band beats the decile-matched controls, the natal-only sub-score is at or above the 95th placebo percentile, there are at least 30 events, and the effect is positive in at least 60% of folds. Otherwise "no demonstrated edge". Any verdict stays labelled research-grade with hand-set weights. A sample chart can never earn "edge candidate"; its result is labelled a pipeline check only. Action labels show the verdict beside them.

## Tab content

SAMPLE banner where relevant, chart table, today's score and band, raised/lowered factor lists, backtest table with folds, controls and caveats, disclaimer.

## Testing

- Lagna matches a published reference value for one chart; invalid profiles are rejected.
- Navigator GETs are refused for proxied or non-local callers without a token.
- Lineage contributions sum to the score, with numeric assertions on real computed days.
- Leakage: altering every price after the entry point leaves all scores up to that point identical, including through the embargo.
- Placebo run is deterministic under a seed.
- Bands are correct at each boundary, including 20/21 and 80/81.
- A planted-signal fixture shows the backtest detects a real edge, and pure noise shows none, so the test cannot pass vacuously.
- Postgres down gives 503 and the Flask app still boots.
- Birth data never appears in logs.
- Verified in the real page with the browser before reporting done.

## Later phases (each gets its own spec)

2. Full natal chart: Shadbala, Avastha, yogas in the score, Western system switch.
3. All five markets, CSV and PDF export. Confirm `^GSPC` rows, source NASDAQ, refresh Bank Nifty.
4. Day ranking for 30, 90, 365 days, top 20 lists, calendar heatmap.
5. Analog comparison for high-scoring dates: at least 5 similar dates with Nifty and Bank Nifty returns, VIX change, top 5 sectors, win ratio, max drawdown, next-5-day return.
6. 3D scatter and animated natal planet model.
7. Pattern clustering, cycle recognition, regime detection, narrative explanation.

Bead SBC_Tool-9zw (lagna falls back to Mumbai for non-Indian anchors) stays open: Phase 1 avoids that code path by using `lagna_at`.

## Stress Test Results: AstroTrade Navigator Phase 1

### Resolved Decisions
- Leakage: HistVal uses an embargo equal to the return horizon, with a test altering all prices after entry.
- Execution: entry at T's open, using data to T-1's close.
- Band occupancy: bands unchanged, occupancy reported, any rescaling is a later user decision.
- Placebo: full-pipeline placebos, two percentiles, shared ephemeris, 10-minute limit.
- Security: guard on all navigator reads and writes, proxied callers need a token, required Postgres password.
- Caching: keys include data_asof, engine_version and chart_hash. Future scores are not cached.
- Natal inputs: coordinate-based `lagna_at`, IANA timezone, strict validation.
- Reporting: "edge candidate" verdict fixed in code ahead of results.
- Backtest jobs: durable status, heartbeat, single active run per profile.

### Changes Made
All nine are applied in the sections above. All were agreed as recommended. Decile-matched controls are now defined precisely.

### Deferred / Parking Lot
- Encryption at rest for `natal_profile` (accepted risk, Phase 1).
- Band rescaling, pending occupancy results.

### Confidence Assessment
- Overall: Medium-High.
- Areas of concern: extreme bands may be empty; hand-set weight tables are judgement calls; placebo run time is unmeasured; Docker must be running.
