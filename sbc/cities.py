"""City lookup for birth data (B-14): GeoNames cities with population >= 15,000.

data/cities.db (env SBC_CITIES_DB) is built by scripts/seed_cities.py from three
GeoNames dump files (CC BY 4.0, https://www.geonames.org/):

  cities15000.zip        ~33k cities: name, ASCII name, coordinates, population, time zone
  countryInfo.txt        ISO country code -> country name
  admin1CodesASCII.txt   country.admin1 code -> state / province name

search() ranks exact name matches first, then prefixes, then substrings, and
breaks ties by population, so "Delhi" finds Delhi before Delhi Cantonment.
"""

from __future__ import annotations

import csv
import io
import os
import sqlite3
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = Path(os.environ.get("SBC_CITIES_DB") or ROOT / "data" / "cities.db")
GEONAMES_BASE = "https://download.geonames.org/export/dump/"
FILES = ("cities15000.zip", "countryInfo.txt", "admin1CodesASCII.txt")
MAX_LIMIT = 50
USA = {"usa", "us", "united states", "united states of america"}

_SCHEMA = """
CREATE TABLE cities (
    id INTEGER PRIMARY KEY,          -- GeoNames id
    name TEXT NOT NULL,
    ascii_name TEXT NOT NULL,
    country TEXT NOT NULL,
    country_code TEXT NOT NULL,
    admin_name TEXT,
    lat REAL NOT NULL,
    lon REAL NOT NULL,
    population INTEGER NOT NULL,
    timezone TEXT
);
CREATE INDEX cities_ascii ON cities (ascii_name COLLATE NOCASE);
CREATE INDEX cities_name ON cities (name COLLATE NOCASE);
"""


def _countries(text: str) -> dict[str, str]:
    out = {}
    for line in text.splitlines():
        if line.startswith("#") or not line.strip():
            continue
        cols = line.split("\t")
        if len(cols) > 4:
            out[cols[0]] = cols[4]
    return out


def _admin1(text: str) -> dict[str, str]:
    out = {}
    for line in text.splitlines():
        cols = line.split("\t")
        if len(cols) >= 2:
            out[cols[0]] = cols[1]
    return out


def build(source_dir: Path, db_path: Path | None = None) -> int:
    """Build the cities table from the GeoNames files in `source_dir`; returns rows written."""
    db_path = db_path or DB_PATH
    countries = _countries((source_dir / "countryInfo.txt").read_text(encoding="utf-8"))
    admin1 = _admin1((source_dir / "admin1CodesASCII.txt").read_text(encoding="utf-8"))
    rows = []
    with zipfile.ZipFile(source_dir / "cities15000.zip") as zf, zf.open("cities15000.txt") as fh:
        reader = csv.reader(io.TextIOWrapper(fh, encoding="utf-8"), delimiter="\t", quoting=csv.QUOTE_NONE)
        for c in reader:
            # geonameid, name, asciiname, alternatenames, lat, lon, feature class, feature code,
            # country code, cc2, admin1, admin2, admin3, admin4, population, elevation, dem, tz, modified
            code = c[8]
            rows.append((int(c[0]), c[1], c[2] or c[1], countries.get(code, code), code,
                         admin1.get(f"{code}.{c[10]}"), float(c[4]), float(c[5]),
                         int(c[14] or 0), c[17] or None))
    tmp = db_path.with_suffix(".db.tmp")
    tmp.unlink(missing_ok=True)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(tmp))
    try:
        conn.executescript(_SCHEMA)
        conn.executemany("INSERT INTO cities VALUES (?,?,?,?,?,?,?,?,?,?)", rows)
        conn.commit()
    finally:
        conn.close()
    os.replace(tmp, db_path)  # atomic swap: readers never see a half-built table
    return len(rows)


def count(db_path: Path | None = None) -> int:
    path = db_path or DB_PATH
    if not path.exists():
        return 0
    try:
        with sqlite3.connect(str(path)) as conn:
            return int(conn.execute("SELECT COUNT(*) FROM cities").fetchone()[0])
    except sqlite3.Error:
        return 0


def search(q: str, country: str | None = None, limit: int = 20, db_path: Path | None = None) -> list[dict]:
    """Cities whose name or ASCII name contains `q`, best matches first."""
    q = (q or "").strip()
    path = db_path or DB_PATH
    if len(q) < 2 or not path.exists():
        return []
    limit = max(1, min(int(limit), MAX_LIMIT))
    like = f"%{q.replace('%', '').replace('_', '')}%"
    sql = ["SELECT name, country, country_code, admin_name, lat, lon, population, timezone,",
           " CASE WHEN name = :q COLLATE NOCASE OR ascii_name = :q COLLATE NOCASE THEN 0",
           "      WHEN name LIKE :prefix OR ascii_name LIKE :prefix THEN 1 ELSE 2 END AS rank",
           " FROM cities WHERE (name LIKE :like OR ascii_name LIKE :like)"]
    params: dict[str, object] = {"q": q, "prefix": f"{q}%", "like": like, "limit": limit}
    c = (country or "").strip()
    if c.lower() in USA:
        sql.append(" AND country_code = 'US'")
    elif c:
        sql.append(" AND (country LIKE :country OR country_code = :code)")
        params.update(country=f"%{c}%", code=c.upper())
    sql.append(" ORDER BY rank, population DESC LIMIT :limit")
    with sqlite3.connect(str(path)) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("".join(sql), params).fetchall()
    return [{"name": r["name"], "country": r["country"], "country_code": r["country_code"],
             "admin": r["admin_name"], "lat": r["lat"], "lon": r["lon"],
             "population": r["population"], "timezone": r["timezone"]} for r in rows]
