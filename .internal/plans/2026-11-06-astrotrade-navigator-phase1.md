# AstroTrade Navigator Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use beads-superpowers:subagent-driven-development (recommended) or beads-superpowers:executing-plans to implement this plan task-by-task. Each Task becomes a bead (`bd create -t task --parent <epic-id>`). Steps within tasks use checkbox (`- [ ]`) syntax for human readability.

**Goal:** One natal chart, a daily 0-100 score with additive lineage, and a walk-forward Nifty backtest, verified in the running Flask app.

**Architecture:** A new pure-Python package `sbc/navigator/` computes on plain arrays, with one module (`store.py`) touching Postgres. A blueprint and a plain JS tab sit on top. All charts share one precomputed daily ephemeris, so 200 placebos stay fast.

**Tech Stack:** Python 3.11, Flask, pyswisseph, numpy, psycopg 3, Postgres 16 in Docker, plain JS.

Spec: `.internal/specs/2026-11-06-astrotrade-navigator-phase1-design.md`. Brainstorming bead: SBC_Tool-me7.

## Global Constraints

- Run tests with `./venv/Scripts/python -m pytest`. Do not commit or push unless the user asks (project rule; this replaces the usual per-task commit step).
- Sidereal Lahiri positions via `sbc.planets._flags()`. No new CDN dependencies. No FastAPI or React.
- Weight tables are hand-set before any returns are examined and are never fitted.
- Entry at T's open; the T-1 close is the last input. HistVal embargo equals the horizon.
- Birth data is never logged, never committed, never in URLs beyond the numeric id.
- Output language is weighted-factor, never mystical. Action labels always carry the unvalidated research disclaimer.
- Tests must assert real numbers; no vacuous tests.

## File Structure

| File | Responsibility |
|---|---|
| `sbc/navigator/__init__.py` | Package marker |
| `sbc/navigator/weights.py` | Tables, `WEIGHTS_VERSION` |
| `sbc/navigator/profile.py` | Validation, `chart_hash`, `lagna_at`, `natal_points`, `SAMPLE_PROFILE` |
| `sbc/navigator/ephemeris.py` | `SkyTable`: shared daily positions |
| `sbc/navigator/terms.py` | Transit, Moon, Dasha, Strength, Vol terms (arrays and factors) |
| `sbc/navigator/scoring.py` | Combination, HistVal, bands, actions, rounding |
| `sbc/navigator/backtest.py` | Folds, metrics, controls, placebos, verdict |
| `sbc/navigator/store.py` | Postgres access, migrations, job state |
| `sbc/navigator/migrations/001_init.sql` | Schema |
| `sbc/api/blueprints/navigator_bp.py` | Routes and guard |
| `static/js/navigator.js` | Tab logic |
| `sbc/yogas.py` | Pratyantar added |
| `sbc/app_factory.py`, `templates/index.html`, `static/style.css`, `docker-compose.navigator.yml`, `.env.example`, `requirements.txt` | Wiring |
| `tests/test_navigator_*.py` | Tests |

---

### Task 1: Postgres service and store skeleton

**Files:** Modify `requirements.txt`, `.dockerignore`. Create `docker-compose.navigator.yml`, `.env.example`, `sbc/navigator/__init__.py`, `sbc/navigator/migrations/001_init.sql`, `sbc/navigator/store.py`, `tests/test_navigator_store.py`.

**Interfaces:** Produces `store.connect()`, `store.migrate()`, `store.StoreUnavailable`.

**Acceptance Criteria:**
- `docker compose -f docker-compose.navigator.yml up -d postgres` binds to `127.0.0.1:5433` and compose refuses to start without `NAV_PG_PASSWORD`.
- `create_app()` succeeds with Postgres down; import of `store` makes no connection.
- `migrate()` is idempotent.

- [ ] **Step 1: Create `docker-compose.navigator.yml`** with this content. `docker-compose.yml` stays unchanged; the explicit project name keeps `down --remove-orphans` on it from removing this service.

```yaml
name: sbc-navigator

services:
  postgres:
    image: postgres:16-alpine
    container_name: sbc-nav-postgres
    ports:
      - "127.0.0.1:5433:5432"
    environment:
      - POSTGRES_DB=navigator
      - POSTGRES_USER=navigator
      - POSTGRES_PASSWORD=${NAV_PG_PASSWORD:?set NAV_PG_PASSWORD in .env}
    volumes:
      - nav_pgdata:/var/lib/postgresql/data
    restart: unless-stopped

volumes:
  nav_pgdata: {}
```

Add `psycopg[binary]>=3.2,<4.0` to `requirements.txt` and install it. Create `.env.example` containing `NAV_PG_PASSWORD=` and `NAV_DATABASE_URL=postgresql://navigator:CHANGE_ME@127.0.0.1:5433/navigator`. Regenerate `requirements.lock` by the repo's existing method.

- [ ] **Step 2: Write the schema** in `001_init.sql`.

```sql
CREATE TABLE IF NOT EXISTS natal_profile (
  id BIGSERIAL PRIMARY KEY, label TEXT NOT NULL, is_sample BOOLEAN NOT NULL,
  birth_date DATE NOT NULL, birth_time TIME NOT NULL, tz TEXT NOT NULL,
  lat DOUBLE PRECISION NOT NULL, lon DOUBLE PRECISION NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS daily_score (
  profile_id BIGINT NOT NULL REFERENCES natal_profile(id) ON DELETE CASCADE,
  day DATE NOT NULL, weights_version TEXT NOT NULL, data_asof DATE NOT NULL,
  engine_version TEXT NOT NULL, chart_hash TEXT NOT NULL,
  score NUMERIC NOT NULL, band TEXT NOT NULL, action TEXT NOT NULL, lineage JSONB NOT NULL,
  PRIMARY KEY (profile_id, day, weights_version, data_asof, engine_version, chart_hash));
CREATE TABLE IF NOT EXISTS backtest_run (
  id BIGSERIAL PRIMARY KEY,
  profile_id BIGINT NOT NULL REFERENCES natal_profile(id) ON DELETE CASCADE,
  instrument TEXT NOT NULL, weights_version TEXT NOT NULL, data_asof DATE NOT NULL,
  engine_version TEXT NOT NULL, chart_hash TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('queued','running','done','failed')),
  heartbeat_at TIMESTAMPTZ, error TEXT, params JSONB NOT NULL, folds JSONB, results JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE UNIQUE INDEX IF NOT EXISTS one_active_run ON backtest_run(profile_id)
  WHERE status IN ('queued','running');
```

- [ ] **Step 3: Write failing tests**

```python
import importlib, os, pytest
from sbc.navigator import store

def test_connect_without_url_raises_unavailable(monkeypatch):
    monkeypatch.delenv("NAV_DATABASE_URL", raising=False)
    with pytest.raises(store.StoreUnavailable):
        store.connect()

def test_app_boots_with_postgres_unreachable(monkeypatch):
    monkeypatch.setenv("NAV_DATABASE_URL", "postgresql://x:y@127.0.0.1:1/none")
    from sbc.app_factory import create_app
    assert create_app().url_map is not None

@pytest.mark.skipif(not os.environ.get("NAV_TEST_DATABASE_URL"), reason="needs Postgres")
def test_migrate_is_idempotent(monkeypatch):
    monkeypatch.setenv("NAV_DATABASE_URL", os.environ["NAV_TEST_DATABASE_URL"])
    store.migrate(); store.migrate()
    with store.connect() as c:
        assert c.execute("select count(*) from information_schema.tables where table_name='backtest_run'").fetchone()[0] == 1
```

- [ ] **Step 4: Run** `./venv/Scripts/python -m pytest tests/test_navigator_store.py -v`. Expected: FAIL, no module `sbc.navigator.store`.

- [ ] **Step 5: Implement**

```python
"""The only Navigator module that touches Postgres."""
from __future__ import annotations
import os
from pathlib import Path
import psycopg

MIGRATIONS = Path(__file__).parent / "migrations"

class StoreUnavailable(RuntimeError):
    """Postgres is not configured or not reachable."""

def connect() -> psycopg.Connection:
    url = os.environ.get("NAV_DATABASE_URL", "").strip()
    if not url:
        raise StoreUnavailable("NAV_DATABASE_URL is not set")
    try:
        return psycopg.connect(url, connect_timeout=3)
    except psycopg.OperationalError as exc:
        raise StoreUnavailable("Postgres is unreachable") from exc

def migrate() -> None:
    with connect() as conn:
        for path in sorted(MIGRATIONS.glob("*.sql")):
            conn.execute(path.read_text(encoding="utf8"))
```

The error message must not include the URL, as it holds the password.

- [ ] **Step 6: Run tests.** Expected: PASS, with the migrate test run against a live `NAV_TEST_DATABASE_URL` before this task closes.

### Task 2: Pratyantar in Vimshottari

**Files:** Modify `sbc/yogas.py:52-110`. Test `tests/test_navigator_dasha.py`.

**Interfaces:** Produces `vimshottari(...)["mahadashas"][i]["antardashas"][j]["pratyantars"]` as `[{lord,start,end}]`, and `["at"]["pratyantar"]`.

**Acceptance Criteria:** Existing keys unchanged. Nine pratyantars per antar, contiguous, spanning the antar exactly, first lord equals the antar lord.

- [ ] **Step 1: Failing test**

```python
import datetime as dt
from sbc.yogas import vimshottari

def _d(s): return dt.datetime.fromisoformat(s)

def test_pratyantars_partition_each_antar():
    v = vimshottari(100.0, "1980-05-05", "2020-01-01")
    antar = v["mahadashas"][1]["antardashas"][2]
    p = antar["pratyantars"]
    assert len(p) == 9 and p[0]["lord"] == antar["lord"]
    assert abs((_d(p[-1]["end"]) - _d(antar["end"])).total_seconds()) < 2
    assert all(a["end"] == b["start"] for a, b in zip(p, p[1:]))

def test_at_names_pratyantar():
    assert vimshottari(100.0, "1980-05-05", "2020-01-01")["at"]["pratyantar"] is not None
```

- [ ] **Step 2: Run; expected FAIL** with `KeyError: 'pratyantars'`.

- [ ] **Step 3: Implement.** Inside the antar loop, before `antars.append`:

```python
pratyantars = []
pcursor = acursor
p_idx = ant_idx
antar_days = alen.total_seconds() / 86400.0
for _p in range(9):
    plord, pyears = VIMSHOTTARI[p_idx]
    plen = dt.timedelta(days=antar_days * pyears / 120.0)
    pratyantars.append({"lord": plord, "start": pcursor.isoformat(),
                        "end": (pcursor + plen).isoformat()})
    pcursor += plen
    p_idx = (p_idx + 1) % 9
```

Add `"pratyantars": pratyantars` to the antar dict. After `at_antar`, resolve `at_pratyantar` the same way and add `"pratyantar"` to `at`.

- [ ] **Step 4: Run** the new test and `tests/` matches for `yogas`. Expected: PASS.

### Task 3: Profile validation, lagna and sample chart

**Files:** Create `sbc/navigator/profile.py`, `tests/test_navigator_profile.py`.

**Interfaces:** Produces `Profile` (frozen dataclass: `label, is_sample, birth_date, birth_time, tz, lat, lon`), `validate(dict) -> Profile`, `lagna_at(date,time,tz,lat,lon) -> float`, `natal_points(Profile) -> dict[str,float]` (nine grahas plus `"Lagna"`), `chart_hash(Profile) -> str`, `SAMPLE_PROFILE`.

**Acceptance Criteria:** Invalid time, tz or coordinates raise `ValueError` with no default applied. Lagna matches a direct `swe.houses_ex` reference and changes with coordinates. Sample has `is_sample=True` and label beginning `SAMPLE`.

- [ ] **Step 1: Failing tests**

```python
import pytest, swisseph as swe
from sbc.navigator import profile as P
from sbc.engine import _julday, _utc_from_local

GOOD = dict(label="x", birth_date="1985-03-14", birth_time="06:30",
            tz="Asia/Kolkata", lat=12.97, lon=77.59)

@pytest.mark.parametrize("field,bad", [("birth_time",""),("birth_time","25:00"),("tz","Mars/Olympus"),
                                       ("lat",91),("lon",-181),("birth_date","1985-13-01")])
def test_invalid_rejected(field, bad):
    with pytest.raises(ValueError):
        P.validate({**GOOD, field: bad})

def test_lagna_uses_coordinates_not_city():
    a = P.lagna_at("1985-03-14","06:30","Asia/Kolkata",12.97,77.59)
    b = P.lagna_at("1985-03-14","06:30","Asia/Kolkata",51.5,-0.12)
    assert abs(a-b) > 1
    jd = _julday(_utc_from_local("1985-03-14","06:30","Asia/Kolkata"))
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    assert a == pytest.approx(swe.houses_ex(jd,12.97,77.59,b"W",swe.FLG_SIDEREAL)[1][0] % 360, abs=1e-6)

def test_natal_points_include_lagna_and_ketu_opposite_rahu():
    n = P.natal_points(P.validate(GOOD))
    assert len(n) == 10 and abs((n["Rahu"]+180)%360 - n["Ketu"]) < 1e-3

def test_hash_changes_with_input():
    assert P.chart_hash(P.validate(GOOD)) != P.chart_hash(P.validate({**GOOD,"lat":13.0}))

def test_sample_is_marked():
    assert P.SAMPLE_PROFILE.is_sample and P.SAMPLE_PROFILE.label.startswith("SAMPLE")
```

The executor must also check one lagna against a published reference (Swiss Ephemeris test page or a named chart) and record its source in a test comment.

- [ ] **Step 2: Run; expected FAIL**, module missing.

- [ ] **Step 3: Implement**

```python
"""Natal inputs. Rejects bad input; never defaults. `_utc_from_local` silently
falls back to Kolkata, so tz is validated here first."""
from __future__ import annotations
import datetime as dt, hashlib, json
from dataclasses import asdict, dataclass
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
import swisseph as swe
from sbc.engine import _julday, _utc_from_local
from sbc.planets import positions

@dataclass(frozen=True)
class Profile:
    label: str; is_sample: bool; birth_date: str; birth_time: str
    tz: str; lat: float; lon: float

def validate(d: dict) -> Profile:
    try:
        date = dt.date.fromisoformat(str(d["birth_date"])).isoformat()
        time = dt.time.fromisoformat(str(d["birth_time"])).strftime("%H:%M:%S")
        ZoneInfo(str(d["tz"]))
        lat, lon = float(d["lat"]), float(d["lon"])
    except (KeyError, ValueError, TypeError, ZoneInfoNotFoundError) as exc:
        raise ValueError("invalid birth data") from exc
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        raise ValueError("invalid birth data")
    return Profile(str(d.get("label") or "Unnamed"), bool(d.get("is_sample")),
                   date, time, str(d["tz"]), lat, lon)

def lagna_at(date, time, tz, lat, lon) -> float:
    jd = _julday(_utc_from_local(date, time, tz))
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    return float(swe.houses_ex(jd, lat, lon, b"W", swe.FLG_SIDEREAL)[1][0] % 360.0)

def natal_points(p: Profile) -> dict[str, float]:
    jd = _julday(_utc_from_local(p.birth_date, p.birth_time, p.tz))
    planets, _ = positions(jd)
    out = {x["name"]: x["longitude"] for x in planets
           if x["name"] not in ("Uranus", "Neptune", "Pluto")}
    out["Lagna"] = lagna_at(p.birth_date, p.birth_time, p.tz, p.lat, p.lon)
    return out

def chart_hash(p: Profile) -> str:
    d = asdict(p); d.pop("label")
    return hashlib.sha256(json.dumps(d, sort_keys=True).encode()).hexdigest()[:16]

SAMPLE_PROFILE = Profile("SAMPLE (fictional chart)", True, "1980-01-15", "12:00:00",
                         "Asia/Kolkata", 19.076, 72.878)
```

- [ ] **Step 4: Run; expected PASS.**

### Task 4: Weight tables and shared ephemeris

**Files:** Create `sbc/navigator/weights.py`, `sbc/navigator/ephemeris.py`, `tests/test_navigator_ephemeris.py`.

**Interfaces:** Produces `weights.WEIGHTS_VERSION`, `ASPECTS`, `ASPECT_WEIGHT(planet, point, aspect) -> float`, `MOON_*`, `DASHA_LORD`, `STRENGTH_*`, `TERM_WEIGHTS`. Produces `SkyTable` dataclass: `days: list[str]`, `lon: dict[str,np.ndarray]`, `retro: dict[str,np.ndarray]`, built by `build_sky(days) -> SkyTable` at 09:15 IST; bodies are Sun to Saturn, Rahu, Ketu.

**Acceptance Criteria:** Required examples hold exactly: `ASPECT_WEIGHT("Jupiter","Jupiter","TRI")==40`, `("Mars","Mercury","SQ")==-20`, `("Saturn","Moon","OPP")==-35`. `TERM_WEIGHTS` sum to 1. Sky longitudes equal `positions()` for 3 sampled days.

- [ ] **Step 1: Failing tests**

```python
import pytest
from sbc.navigator import weights as W
from sbc.navigator.ephemeris import build_sky
from sbc.engine import _julday, _utc_from_local
from sbc.planets import positions

@pytest.mark.parametrize("a,b", [(("Jupiter","Jupiter","TRI"),40),(("Mars","Mercury","SQ"),-20),(("Saturn","Moon","OPP"),-35)])
def test_required_examples(a,b): assert W.ASPECT_WEIGHT(*a) == b

def test_term_weights_sum(): assert sum(W.TERM_WEIGHTS.values()) == pytest.approx(1)

def test_sky_matches_positions():
    day = "2020-06-15"
    sky = build_sky([day])
    ps,_ = positions(_julday(_utc_from_local(day,"09:15","Asia/Kolkata")))
    for p in ps:
        if p["name"] in sky.lon:
            assert sky.lon[p["name"]][0] == pytest.approx(p["longitude"], abs=1e-3)
```

- [ ] **Step 2: Run; expected FAIL.**

- [ ] **Step 3: Implement `weights.py`**

```python
"""Hand-set research tables. Written before any return was examined; never fitted.
Change any value: bump WEIGHTS_VERSION and disclose the new table as in-sample."""
WEIGHTS_VERSION = "nav-1"
TERM_WEIGHTS = {"transit":.25,"moon":.20,"dasha":.20,"strength":.15,"histval":.10,"vol":.10}
ASPECTS = {"CONJ":0.0,"SXT":60.0,"SQ":90.0,"TRI":120.0,"OPP":180.0}
ORB = 3.0
TRANSIT_BODIES = ["Sun","Moon","Mars","Mercury","Jupiter","Venus","Saturn","Rahu","Ketu"]
BENEFIC = {"Jupiter":1.0,"Venus":.75,"Moon":.5,"Mercury":.4,"Sun":.1,
           "Mars":-.5,"Saturn":-.875,"Rahu":-.5,"Ketu":-.5}
NODE_FACTOR = 0.5
ASPECT_SIGN = {"TRI":1.0,"SXT":.6,"CONJ":None,"SQ":-1.0,"OPP":-1.0}
_EXPLICIT = {("Jupiter","Jupiter","TRI"):40.0,("Mars","Mercury","SQ"):-20.0,("Saturn","Moon","OPP"):-35.0}

def ASPECT_WEIGHT(planet, point, aspect) -> float:
    if (planet, point, aspect) in _EXPLICIT:
        return _EXPLICIT[(planet, point, aspect)]
    b = BENEFIC[planet]
    sign = ASPECT_SIGN[aspect]
    w = 30.0 * b if sign is None else 20.0 * sign * (1.0 + b if sign > 0 else 1.0 - b)
    # Ketu always mirrors Rahu, so each carries half and the axis counts once.
    return w * NODE_FACTOR if planet in ("Rahu", "Ketu") else w

# Moon Sentiment Score parts, summing to at most +/-100.
MOON_PHASE = 30.0    # waxing +, waning -, scaled by illumination distance from full/new
MOON_TITHI_RIKTA = -20.0   # tithis 4, 9, 14 of either paksha
MOON_TITHI_NANDA = 20.0    # tithis 1, 6, 11
MOON_SIGN = {0:15,1:25,2:5,3:20,4:5,5:0,6:10,7:-25,8:10,9:0,10:0,11:-10}  # sign_index, Aries=0
MOON_NAKSHATRA_DRUVA = 25.0   # fixed stars
MOON_NAKSHATRA_UGRA = -25.0   # fierce stars
DRUVA = {"Rohini","U.Phalguni","U.Ashadha","U.Bhadrapada"}  # sbc.nakshatra spellings
UGRA = {"Bharani","Magha","P.Phalguni","P.Ashadha","P.Bhadrapada"}
DASHA_LORD = {"Jupiter":40,"Venus":30,"Mercury":20,"Moon":15,"Sun":5,"Mars":-10,"Ketu":-20,"Rahu":-25,"Saturn":-30}
DASHA_LEVELS = {"maha":.5,"antar":.3,"pratyantar":.2}
STRENGTH_EXALTED, STRENGTH_DEBILITATED, STRENGTH_COMBUST, STRENGTH_RETRO = 20.0, -20.0, -15.0, 5.0
HIST_MIN_YEARS, HIST_HORIZON = 3, 5
```

A test in Task 5 asserts every nakshatra name exists. The table is a judgement call and is disclosed on the page.

- [ ] **Step 4: Implement `ephemeris.py`**

```python
"""One daily position table, shared by every chart (spec: placebos)."""
from __future__ import annotations
import datetime as dt
from dataclasses import dataclass
import numpy as np
from sbc.engine import _julday, _utc_from_local
from sbc.navigator.weights import TRANSIT_BODIES
from sbc.planets import positions

@dataclass
class SkyTable:
    days: list[str]
    lon: dict[str, np.ndarray]
    retro: dict[str, np.ndarray]

def build_sky(days: list[str]) -> SkyTable:
    lon = {b: np.zeros(len(days)) for b in TRANSIT_BODIES}
    retro = {b: np.zeros(len(days), bool) for b in TRANSIT_BODIES}
    for i, day in enumerate(days):
        ps, _ = positions(_julday(_utc_from_local(day, "09:15", "Asia/Kolkata")))
        for p in ps:
            if p["name"] in lon:
                lon[p["name"]][i] = p["longitude"]
                retro[p["name"]][i] = p["retrograde"]
    return SkyTable(days, lon, retro)
```

- [ ] **Step 5: Run; expected PASS.**

### Task 5: Term calculators with factors

**Files:** Create `sbc/navigator/terms.py`, `tests/test_navigator_terms.py`.

**Interfaces:** Consumes `SkyTable`, `natal_points`. Produces, each returning a `Term(values: np.ndarray, raw: np.ndarray, factors: Callable[[int], list[dict]])` where values are 0-100 and a factor is `{term,label,raw}`:
- `transit_term(sky, natal)`
- `moon_term(sky)`
- `dasha_term(sky, moon_natal_lon, birth_date)`
- `strength_term(sky)`, with `note="partial: no Shadbala/Avastha yet"` in each factor
- `vol_term(days, vix_by_day)`: T-1 close percentile; neutral 50 flagged `"neutral": True` when missing

**Acceptance Criteria:** All values in [0,100]. Factors for a day reproduce its raw value. An exact aspect gets full weight; at the orb edge, none. Vol uses only values strictly before T. Table names exist in `sbc.nakshatra`.

- [ ] **Step 1: Failing tests**

```python
import numpy as np, pytest
from sbc.navigator import terms as T
from sbc.navigator.ephemeris import SkyTable
from sbc.navigator import weights as W

def sky(jup):
    n=len(jup); b=W.TRANSIT_BODIES
    lon={k:np.full(n,200.0) for k in b}; lon["Jupiter"]=np.array(jup,float)
    return SkyTable([f"2020-01-{i+1:02d}" for i in range(n)],lon,{k:np.zeros(n,bool) for k in b})

def test_orb_taper_linear():
    natal={"Jupiter":0.0}
    t=T.transit_term(sky([120.0,121.5,123.0]),natal)
    assert t.raw[0]==pytest.approx(40) and t.raw[1]==pytest.approx(20) and t.raw[2]==pytest.approx(0)
    assert t.values[0]==pytest.approx(70)

def test_vol_ignores_same_day_value():
    days=[f"2021-01-{i+1:02d}" for i in range(9)]+["2021-02-01"]
    vix={d:float(i) for i,d in enumerate(days)}
    a=T.vol_term(days,vix,window=5).values[-1]
    vix[days[-1]]=9999.0
    assert T.vol_term(days,vix,window=5).values[-1]==a

def test_missing_vix_is_flagged_neutral():
    t=T.vol_term(["2021-01-01"],{})
    assert t.values[0]==50 and t.factors(0)[0]["neutral"] is True

def test_moon_raw_bounded_and_nakshatra_names_real():
    from sbc.nakshatra import nakshatra_of
    s=sky([0.0]*360); s.lon["Moon"]=np.arange(360.0)
    r=T.moon_term(s).raw
    assert r.min()>=-100 and r.max()<=100 and r.std()>5
    names={nakshatra_of(float(x))[0] for x in range(360)}
    assert W.DRUVA|W.UGRA <= names
```

- [ ] **Step 2: Run; expected FAIL.**

- [ ] **Step 3: Implement.** Core of transit (numpy, one pass per planet, point and aspect):

```python
from dataclasses import dataclass
from typing import Callable
import numpy as np
from sbc import nakshatra as N
from sbc.navigator import weights as W
from sbc.planets import COMBUST_ORB, DEBIL, EXALT
from sbc.yogas import vimshottari

@dataclass
class Term:
    values: np.ndarray; raw: np.ndarray; factors: Callable[[int], list[dict]]

def _scale(raw): return (np.clip(raw, -100, 100) + 100) / 2

def transit_term(sky, natal):
    n = len(sky.days); raw = np.zeros(n); parts = []
    for planet in W.TRANSIT_BODIES:
        for point, nlon in natal.items():
            sep = np.abs((sky.lon[planet] - nlon + 180) % 360 - 180)
            for code, angle in W.ASPECTS.items():
                orb_factor = np.clip(1 - np.abs(sep - angle) / W.ORB, 0, 1)
                w = W.ASPECT_WEIGHT(planet, point, code)
                contrib = w * orb_factor
                raw += contrib
                parts.append((f"{planet} {code} natal {point}", contrib))
    def factors(i):
        return [{"term":"transit","label":l,"raw":round(float(c[i]),3)} for l,c in parts if c[i]]
    return Term(_scale(raw), raw, factors)
```

`strength_term`: for each of the seven planets, add `STRENGTH_EXALTED` if the sign index equals `EXALT[name]`, `STRENGTH_DEBILITATED` if `DEBIL[name]`, `STRENGTH_COMBUST` if within `COMBUST_ORB`, `STRENGTH_RETRO` if retrograde; `values = np.clip(50 + raw/2, 0, 100)`; labels like `Saturn debilitated` with `note`.

`moon_term`: sum of phase `MOON_PHASE*cos(radians((moon-sun)%360 - 90))`, rikta or nanda tithi points, `MOON_SIGN`, nakshatra group; clip to ±100, `_scale`. Each part is a factor.

`dasha_term`: call `vimshottari(moon_natal_lon, birth_date, day)` once, walk pre-flattened period lists with `np.searchsorted` for speed; `raw = Σ DASHA_LEVELS[level] * DASHA_LORD[lord]`, `_scale`.

`vol_term(days, vix_by_day, window=252)`: for index i, percentile of `vix[i-1]` within the previous `window` values before it, `values = 100 - pct`; if fewer than 20 values or the T-1 value is missing, 50 and `neutral=True`.

- [ ] **Step 4: Run; expected PASS.**

### Task 6: Score combination, HistVal, lineage

**Files:** Create `sbc/navigator/scoring.py`, `tests/test_navigator_scoring.py`.

**Interfaces:** Produces `band_of(int) -> str`, `action_of(band) -> str`, `hist_val(base_scores, returns, horizon, min_sessions) -> np.ndarray`, `combine(terms: dict[str,np.ndarray]) -> np.ndarray`, `lineage(terms_at_day: dict[str,float], factors: list[dict]) -> dict` with `{score:int, contributions:[...], raised:[...], lowered:[...]}`, and `score_series(sky, profile, opens, closes, vix) -> ScoreSeries(days,score,base,terms)`.

**Acceptance Criteria:** Exact band boundaries (20/21, 40/41, 60/61, 80/81). Displayed contributions sum exactly to the displayed integer score on real days. HistVal is neutral for the first 3 years and unchanged when returns inside the embargo change. No factor text has mystical wording.

- [ ] **Step 1: Failing tests**

```python
import numpy as np, pytest
from sbc.navigator import scoring as S

@pytest.mark.parametrize("v,b",[(0,"No Trading"),(20,"No Trading"),(21,"Very Defensive"),(40,"Very Defensive"),
  (41,"Normal"),(60,"Normal"),(61,"High Probability"),(80,"High Probability"),(81,"Exceptional Setup"),(100,"Exceptional Setup")])
def test_bands(v,b): assert S.band_of(v)==b

def test_hist_val_embargo_and_warmup():
    n=1200; base=np.random.default_rng(0).uniform(30,70,n); r=np.random.default_rng(1).normal(0,.01,n)
    h=S.hist_val(base,r,horizon=5,min_sessions=756)
    assert (h[:756]==50).all()
    r2=r.copy(); r2[1000-4:]=9.0     # within the embargo for T=1000, or later
    assert S.hist_val(base,r2,5,756)[:1001].tolist()==h[:1001].tolist()

def test_contributions_sum_exactly():
    terms=dict(transit=61.37,moon=48.91,dasha=55.13,strength=47.77,histval=50.0,vol=62.5)
    out=S.lineage(terms,[])
    assert round(sum(c["contribution"] for c in out["contributions"]),2)==out["score"]
    assert out["raised"][0]["term"]=="transit"
```

Add a test using the real sample chart over 50 real Nifty days asserting the same exact sum.

- [ ] **Step 2: Run; expected FAIL.**

- [ ] **Step 3: Implement**

```python
BANDS=[(20,"No Trading"),(40,"Very Defensive"),(60,"Normal"),(80,"High Probability"),(100,"Exceptional Setup")]
ACTIONS={"Exceptional Setup":"Trade Aggressively","High Probability":"Trade Normally","Normal":"Reduce Position Size",
         "Very Defensive":"Stay Cash","No Trading":"Avoid Market Entirely"}
def band_of(s): return next(n for hi,n in BANDS if s<=hi)
def action_of(b): return ACTIONS[b]

def hist_val(base, returns, horizon, min_sessions):
    """base: score from the other five terms (renormalised to 100%). returns[t]: forward
    return from t's open over `horizon` sessions. Day t may use t' only if t'+horizon <= t."""
    n=len(base); out=np.full(n,50.0); rounded=np.rint(base).astype(int)
    for t in range(min_sessions,n):
        usable=t-horizon
        if usable<=0: continue
        past=returns[:usable]; b=np.array([band_of(int(v)) for v in rounded[:usable]])
        same=past[b==band_of(int(rounded[t]))]
        if same.size<30: continue
        out[t]=100.0*float((past<same.mean()).mean())
    return out
```

Compute band labels once with `np.digitize` for speed when implementing, since this runs per placebo. `returns[:usable]` covers `t' < t-horizon`, so the last window used closes before t.

`lineage`: contribution `= TERM_WEIGHTS[k]*v`, rounded to 2dp; `score = int(round(sum))`; the residual `score - sum(rounded)` is added to the largest-magnitude contribution. A term's contribution relative to a neutral 50 decides `raised` (positive) or `lowered`, sorted by size. Include `factors` per term.

- [ ] **Step 4: Run; expected PASS.**

### Task 7: Walk-forward backtest, controls, placebos, verdict

**Files:** Create `sbc/navigator/backtest.py`, `tests/test_navigator_backtest.py`, and a frozen fixture `tests/fixtures/navigator_nifty_sample.csv` (a copy of 500 Nifty rows).

**Interfaces:** Consumes `score_series`, `sbc.stats.bh_adjust`, `shift_pvalue`. Produces `run(profile, ohlc, vix, sky, params, on_progress=None) -> dict` with `{bands:{name:{days,events,mean_oc,mean_oo_1,mean_oo_5,vol,max_dd,hit,win,sharpe,excess_vs_control,p,q,insufficient}}, folds:[...], placebo:{full_pct,natal_pct,n,seconds}, verdict, is_sample}`. Also produces `Inputs` (NamedTuple: `profile, ohlc, vix, sky`), `score_for(inputs, min_sessions=756) -> ScoreSeries`, `run_inputs(inputs, params) -> dict` (which `run` wraps), `band_stats(scores, returns) -> dict`. Defaults: `DEFAULT_PARAMS={"cost_bps":10,"n_placebo":200,"seed":1729,"horizons":[1,5],"min_events":30}`.

**Acceptance Criteria:**
- Altering every price after an entry leaves prior scores identical.
- Consecutive same-band days count as one event.
- Planted signal gives a positive excess and low p; pure noise gives neither.
- Same seed gives identical results. Costs reduce returns by the stated amount.
- Sample chart can never yield `edge candidate`.
- Run time recorded, and a 200-placebo run on real data under 10 minutes, else `n` is reduced and disclosed.

- [ ] **Step 1: Failing tests**

```python
import numpy as np, pandas as pd
from sbc.navigator import backtest as B

def test_events_collapse_runs():
    assert B.count_events(np.array([0,1,1,0,1,1,1,0],bool))==2

def test_cost_applied():
    assert B.net(np.array([.01]),cost_bps=10)[0]==pytest.approx(.009)

def test_decile_control_matches_prior_return_decile():
    prior=np.arange(100.0); mask=np.zeros(100,bool); mask[95:]=True; fwd=np.zeros(100); fwd[90:95]=1
    assert B.matched_control_mean(mask,prior,fwd)==pytest.approx(1.0)

def test_verdict_rules():
    good=dict(q=.05,beats_control=True,natal_pct=96,events=40,fold_pos=.7)
    assert B.verdict(good,is_sample=False)=="edge candidate"
    assert B.verdict(good,is_sample=True)=="no demonstrated edge"
    for k,v in [("q",.2),("beats_control",False),("natal_pct",90),("events",20),("fold_pos",.5)]:
        assert B.verdict({**good,k:v},False)=="no demonstrated edge"

def test_planted_signal_detected_noise_not(planted_series, noise_series):
    assert B.band_stats(*planted_series)["High Probability"]["p"]<.05
    assert B.band_stats(*noise_series)["High Probability"]["p"]>.05

def test_prices_after_entry_do_not_change_scores(sample_inputs):
    # The fixture has 500 rows, so warm-up must be short or HistVal stays neutral and this test proves nothing.
    a=B.score_for(sample_inputs,min_sessions=120)
    assert np.ptp(a.terms["histval"])>0
    ohlc=sample_inputs.ohlc.copy(); ohlc.iloc[300:,:]=ohlc.iloc[300:,:]*3
    b=B.score_for(sample_inputs._replace(ohlc=ohlc),min_sessions=120)
    assert (a.score[:300]==b.score[:300]).all()

def test_same_seed_same_result(sample_inputs):
    p={"n_placebo":3,"seed":7}
    assert B.run_inputs(sample_inputs,p)["placebo"]==B.run_inputs(sample_inputs,p)["placebo"]
```

Fixtures in the same file: `planted_series` is a score series and returns where days in band 61-80 have +0.5% added; `noise_series` uses `np.random.default_rng(3)` returns. `sample_inputs` loads the frozen CSV and `SAMPLE_PROFILE`.

- [ ] **Step 2: Run; expected FAIL.**

- [ ] **Step 3: User sign-off gate.** Stop and show the user the full `weights.py` tables. Do not run on real returns until they approve them as `nav-1`, or edit them. Synthetic and fixture tests may run first only for pipeline checks; their results are not examined as market evidence.

- [ ] **Step 4: Implement**

Core helpers:

```python
def count_events(mask):
    return int(mask[0]) + int(((mask[1:]) & (~mask[:-1])).sum()) if mask.size else 0

def net(r, cost_bps): return r - cost_bps/10000.0

def matched_control_mean(mask, prior, fwd):
    """Non-band sessions in the same decile of the T-1 session's return."""
    edges=np.nanquantile(prior,np.linspace(.1,.9,9)); dec=np.digitize(prior,edges)
    vals=[fwd[(dec==d)&~mask].mean() for d in dec[mask] if ((dec==d)&~mask).any()]
    return float(np.mean(vals)) if vals else float("nan")

def verdict(b, is_sample):
    ok=(b["q"]<.10 and b["beats_control"] and b["natal_pct"]>=95
        and b["events"]>=30 and b["fold_pos"]>=.60)
    return "edge candidate" if ok and not is_sample else "no demonstrated edge"
```

`run` steps, in order:
1. Align sessions from `ohlc`, compute `oc = close/open-1`, `oo_h = open[t+h]/open[t]-1`.
2. `sky = build_sky(days)` once, reused by all charts.
3. Score the real chart; yearly folds from the first post-warmup year, one test year each, with `fold_pos` = fraction of folds with positive net excess.
4. Per band: metrics net of cost, event count, `insufficient` if under `min_events`, p-value through `sbc.stats.shift_pvalue` with `excess_stat`, control excess.
5. `bh_adjust` across all band × horizon p-values.
6. Placebos: `rng = np.random.default_rng(seed)`; birth instant uniform 1950-2005, lat in [-60,60], lon in [-180,180], tz `"UTC"`. For each, run `score_series` and read top-band excess for the full score and a natal-only sub-score (mean of Transit, Dasha, Strength). `on_progress(i, n)` is called per chart, which keeps the heartbeat alive. If the rate projects past 600 seconds after 10 charts, stop at the count that fits and set `placebo.n` accordingly.
7. Return results, with `verdict` per band and an overall worst-case string.

Maximum drawdown is on the cumulative net-return curve of in-band sessions. `sharpe = mean/std*sqrt(252)`, labelled "Sharpe-like".

- [ ] **Step 5: Run; expected PASS.**

- [ ] **Step 6: Real-data timing.** Run a 200-placebo job on full Nifty once and record seconds. Expected: under 600 or reduced `n` shown.

### Task 8: Store queries and job state

**Files:** Modify `sbc/navigator/store.py`. Test `tests/test_navigator_store.py` (needs `NAV_TEST_DATABASE_URL`).

**Interfaces:** Produces `create_profile(Profile)->int`, `get_profile(id)->Profile|None`, `list_profiles()->[{id,label,is_sample}]`, `ensure_sample()->int`, `cached_score(key)->dict|None`, `save_score(key,row)`, `start_run(profile_id,meta)->(id,is_new)`, `heartbeat(id)`, `finish_run(id,results,folds)`, `fail_run(id,error)`, `get_run(id)->dict|None`, `expire_stale(seconds=120)`.

**Acceptance Criteria:** Repeat `start_run` returns the existing id with `is_new=False`. A run with an old heartbeat becomes `failed` and `get_run` reports it. Changing `data_asof` misses the cache. All SQL is parameterised.

- [ ] **Step 1: Failing tests**

```python
pg = pytest.mark.skipif(not os.environ.get("NAV_TEST_DATABASE_URL"), reason="needs Postgres")

@pg
def test_single_active_run(db):
    pid=store.ensure_sample(); m=dict(instrument="NIFTY",weights_version="w",data_asof="2026-01-01",engine_version="e",chart_hash="h",params={})
    a,new=store.start_run(pid,m); b,again=store.start_run(pid,m)
    assert new and not again and a==b

@pg
def test_stale_run_fails(db):
    pid=store.ensure_sample(); rid,_=store.start_run(pid,dict(instrument="NIFTY",weights_version="w",data_asof="2026-01-01",engine_version="e",chart_hash="h",params={}))
    with store.connect() as c: c.execute("update backtest_run set heartbeat_at=now()-interval '1 hour' where id=%s",(rid,))
    store.expire_stale(120)
    assert store.get_run(rid)["status"]=="failed"

@pg
def test_cache_key_includes_data_asof(db):
    pid=store.ensure_sample(); key=dict(profile_id=pid,day="2026-01-05",weights_version="w",data_asof="2026-01-02",engine_version="e",chart_hash="h")
    store.save_score(key,dict(score=55,band="Normal",action="Reduce Position Size",lineage={}))
    assert store.cached_score(key)["score"]==55
    assert store.cached_score({**key,"data_asof":"2026-01-03"}) is None
```

`db` fixture sets `NAV_DATABASE_URL` from the test URL, runs `migrate()`, truncates tables after the test.

- [ ] **Step 2: Run; expected FAIL.**

- [ ] **Step 3: Implement.** `start_run` inserts with `ON CONFLICT (profile_id) WHERE status IN ('queued','running') DO NOTHING RETURNING id`; if none returned, selects the active row. `expire_stale` updates `running`/`queued` rows whose `COALESCE(heartbeat_at, created_at)` is older than the limit, with error `"run stopped reporting"`. `cached_score` selects on all six key columns. `ensure_sample` inserts `SAMPLE_PROFILE` if no row has `is_sample`.

- [ ] **Step 4: Run with Postgres up; expected PASS.**

### Task 9: Blueprint and access guard

**Files:** Create `sbc/api/blueprints/navigator_bp.py`, `tests/test_navigator_api.py`. Modify `sbc/app_factory.py:38-60` (register).

**Interfaces:** Consumes everything above. Produces the routes in the spec.

**Acceptance Criteria:**
- Non-local GET without a token gets 403; proxied local GET without a token gets 401 or 403; valid token passes.
- Postgres down gives 503 JSON on navigator routes; other routes unaffected.
- Invalid profile POST gives 400 with no echoed birth data.
- `/score` returns lineage summing to score, and future dates are not stored.
- Birth values absent from captured logs.

- [ ] **Step 1: Failing tests**

```python
import pytest
from sbc.app_factory import create_app
from sbc.navigator import store

@pytest.fixture
def client(): return create_app().test_client()

def test_proxied_read_refused(client):
    r=client.get("/api/navigator/profile",headers={"X-Forwarded-For":"8.8.8.8"})
    assert r.status_code in (401,403)

def test_remote_read_refused(client):
    r=client.get("/api/navigator/profile",environ_base={"REMOTE_ADDR":"10.0.0.9"})
    assert r.status_code==403

def test_503_when_store_down(client,monkeypatch):
    def boom(): raise store.StoreUnavailable("x")
    monkeypatch.setattr(store,"connect",boom)
    r=client.get("/api/navigator/profile"); assert r.status_code==503
    assert client.get("/healthz").status_code==200

def test_bad_profile_400(client,monkeypatch):
    r=client.post("/api/navigator/profile",json={"birth_time":"99:99"})
    assert r.status_code==400 and b"99:99" not in r.data
```

- [ ] **Step 2: Run; expected FAIL** (404s).

- [ ] **Step 3: Implement**

```python
navigator_bp = Blueprint("navigator", __name__, url_prefix="/api/navigator")
_PROXY = ("X-Forwarded-For","X-Real-IP","Forwarded")

@navigator_bp.before_request
def _guard():
    token=os.environ.get("SBC_API_TOKEN","").strip()
    if token:
        supplied=request.headers.get("X-API-Token","")
        if supplied and hmac.compare_digest(supplied,token): return None
        return jsonify({"error":"a valid X-API-Token header is required"}),401
    if request.remote_addr in _LOCAL_ADDRS and not any(h in request.headers for h in _PROXY):
        return None
    return jsonify({"error":"navigator is local-only until SBC_API_TOKEN is set"}),403

@navigator_bp.errorhandler(store.StoreUnavailable)
def _down(_): return jsonify({"error":"Navigator database is unavailable. Start Postgres and retry."}),503
```

Import `_LOCAL_ADDRS` from `app_factory` inside the guard to avoid an import cycle. Call `store.migrate()` once lazily on first request, not at import or boot. `POST /backtest` runs `expire_stale()`, `start_run`, and starts a daemon thread only if `is_new`; the thread passes `on_progress` calling `heartbeat`, and wraps everything in `try/except` to `fail_run` with a generic message. `/score` reads ohlc via `sbc.market_store.get_daily("NIFTY")` and `get_daily("INDIAVIX")`, `engine_version` from `sbc.engine_version`, and skips caching when `day > data_asof`. Add the blueprint to `_blueprints()`.

- [ ] **Step 4: Run; expected PASS.**

### Task 10: Navigator tab and real-page verification

**Files:** Create `static/js/navigator.js`. Modify `templates/index.html` (tab button near line 86, pane near line 1592, script near line 1659), `static/style.css`. Test `tests/test_navigator_page.py`.

**Acceptance Criteria:**
- The tab shows the SAMPLE banner, chart table, score and band, raised and lowered lists, backtest table with folds, controls, occupancy, verdict, and disclaimer.
- Action label is displayed next to the verdict and "unvalidated research output".
- Failed or unavailable states show readable messages, not endless polling.
- Works at 375px with no horizontal scroll, in dark and light themes.
- All values are written with `textContent`, not `innerHTML`.

- [ ] **Step 1: Failing test**

```python
def test_tab_present():
    from sbc.app_factory import create_app
    html=create_app().test_client().get("/").get_data(as_text=True)
    assert 'data-tab="tab-navigator"' in html and "navigator.js" in html and "unvalidated research output" in html
```

- [ ] **Step 2: Run; expected FAIL.**

- [ ] **Step 3: Add the markup**

```html
<button class="nav-tab" data-tab="tab-navigator" role="tab" aria-selected="false" aria-controls="tab-navigator">Navigator</button>
```

```html
<div id="tab-navigator" class="tab-pane" role="tabpanel">
  <div id="nav-sample-banner" class="nav-banner" hidden>SAMPLE chart. Results are a pipeline check, not about any real person.</div>
  <p class="nav-disclaimer">Action labels are unvalidated research output, not personal financial advice.</p>
  <section id="nav-chart"></section>
  <section id="nav-score"></section>
  <section id="nav-lineage"></section>
  <section id="nav-backtest"><button id="nav-run">Run backtest</button><div id="nav-backtest-out"></div></section>
</div>
```

- [ ] **Step 4: Write `navigator.js`.** Fetch on first tab open; build rows with `document.createElement` and `textContent`. Poll `GET /backtest/<id>` every 3 seconds, stopping on `done` or `failed`. On non-OK responses, show `body.error`. Match the tab-activation pattern used in `static/js/sector-rotation.js`.

- [ ] **Step 5: Run the full suite:** `./venv/Scripts/python -m pytest -q`. Expected: all pass, Postgres tests included with `NAV_TEST_DATABASE_URL` set.

- [ ] **Step 6: Verify the real page.** Start Docker Postgres and the app via `preview_start`. Open the Navigator tab and confirm:
    - Score and lineage render, and on-screen contributions sum to the score.
    - A backtest runs to completion and shows occupancy and a verdict.
    - Stop Postgres: the tab shows the unavailable message and other tabs still work.
    - No console errors; 375px width has no horizontal scroll.
    Capture a screenshot.

- [ ] **Step 7: Report the band occupancy.** If extreme bands are empty, raise it to the user as a decision, per the spec.

---

## Self-Review

Spec coverage: schema T1 and T8; Pratyantar T2; validation, lagna, sample T3; tables T4; terms T5; score, lineage, bands, actions, HistVal T6; walk-forward, controls, placebos, events, verdict T7; job state T8; security, 503, routes T9; tab, verification T10. No requirements are cut.

Epic and task beads are created at execution, with each task's Acceptance Criteria copied in, per the executing skill.

Known constraint: the Postgres tests are skipped unless `NAV_TEST_DATABASE_URL` is set. A task with Postgres tests may not close on a skip.

## Stress Test Results: Phase 1 plan

### Resolved Decisions
- Rahu and Ketu each carry half weight, so the node axis counts once.
- The user reviews and signs off `weights.py` as `nav-1` before the first real-return run (Task 7).

### Changes Made
- Nakshatra spellings and zero-based Moon sign keys now match `sbc/`.
- Aspect weight formula simplified.
- Leakage test uses a short warm-up and asserts HistVal varies, so it cannot pass vacuously.
- `Inputs`, `score_for`, `run_inputs` and `band_stats` are now declared in Task 7.

### Deferred / Parking Lot
- None beyond the spec's list.

### Confidence Assessment
- Overall: Medium-High. Plan code snippets are unrun until execution, so executors should treat them as a close guide and let the tests decide.
