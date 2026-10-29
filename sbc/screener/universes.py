"""NSE stock universes for the momentum screener.

Constituent lists come from NSE's public archive CSVs (indices) and the
F&O market-lots file; Yahoo symbols are the NSE symbol + ".NS".  Lists
are cached under data/universes/ (one calendar day) so a run works
offline from the last fetch, and a static map covers index symbols
(^NSEI and the sectoral indices).

    load("nifty50")            -> ["RELIANCE.NS", ...]
    load("sector:IT")          -> sectoral constituents
    load("indices")            -> ["^NSEI", "^NSEBANK", ...]
    watchlist("RELIANCE, TCS") -> ["RELIANCE.NS", "TCS.NS"]
"""

from __future__ import annotations

import csv
import datetime as dt
import io
import os
import re
from pathlib import Path

CACHE_DIR = Path(os.environ.get(
    "SBC_UNIVERSE_DIR",
    Path(__file__).resolve().parents[2] / "data" / "universes"))
CACHE_TTL = dt.timedelta(days=1)
_UA = {"User-Agent": "Mozilla/5.0 (SBC-Tool research)",
       "Referer": "https://www.nseindia.com/"}

_INDEX_SYMBOLS = {
    "NIFTY 50": "^NSEI",
    "NIFTY BANK": "^NSEBANK",
    "NIFTY FIN SERVICE": "^CNXFIN",
    "NIFTY FINANCIAL SERVICES": "^CNXFIN",
    "NIFTY IT": "^CNXIT",
    "NIFTY AUTO": "^CNXAUTO",
    "NIFTY FMCG": "^CNXFMCG",
    "NIFTY PHARMA": "^CNXPHARMA",
    "NIFTY METAL": "^CNXMETAL",
    "NIFTY ENERGY": "^CNXENERGY",
    "NIFTY INFRASTRUCTURE": "^CNXINFRA",
    "NIFTY PSU BANK": "^CNXPSUBANK",
    "NIFTY REALTY": "^CNXREALTY",
    "NIFTY MEDIA": "^CNXMEDIA",
    "NIFTY MIDCAP 50": "^NSEMDCP50",
}

_INDICES_CSV = {
    "NIFTY 50": "https://archives.nseindia.com/content/indices/ind_nifty50list.csv",
    "NIFTY NEXT 50": "https://archives.nseindia.com/content/indices/ind_niftynext50list.csv",
    "NIFTY 100": "https://archives.nseindia.com/content/indices/ind_nifty100list.csv",
    "NIFTY 200": "https://archives.nseindia.com/content/indices/ind_nifty200list.csv",
    "NIFTY 500": "https://archives.nseindia.com/content/indices/ind_nifty500list.csv",
    "NIFTY MIDCAP 150": "https://archives.nseindia.com/content/indices/ind_niftymidcap150list.csv",
    "NIFTY SMALLCAP 250": "https://archives.nseindia.com/content/indices/ind_niftysmallcap250list.csv",
    "NIFTY BANK": "https://archives.nseindia.com/content/indices/ind_niftybanklist.csv",
}

_SECTOR_CSVS = {
    "IT": "https://archives.nseindia.com/content/indices/ind_niftyitlist.csv",
    "Auto": "https://archives.nseindia.com/content/indices/ind_niftyautolist.csv",
    "FMCG": "https://archives.nseindia.com/content/indices/ind_niftyfmcglist.csv",
    "Pharma": "https://archives.nseindia.com/content/indices/ind_niftypharmalist.csv",
    "Metal": "https://archives.nseindia.com/content/indices/ind_niftymetallist.csv",
    "Energy": "https://archives.nseindia.com/content/indices/ind_niftyenergylist.csv",
    "Infrastructure": "https://archives.nseindia.com/content/indices/ind_niftyinfralist.csv",
    "PSU Bank": "https://archives.nseindia.com/content/indices/ind_niftypsubanklist.csv",
    "Realty": "https://archives.nseindia.com/content/indices/ind_niftyrealtylist.csv",
    "Media": "https://archives.nseindia.com/content/indices/ind_niftymedialist.csv",
    "Financial Services": "https://archives.nseindia.com/content/indices/ind_niftyfinancelist.csv",
}

_FNO_CSV = ("https://archives.nseindia.com/content/fo/"
            "fo_mktlots.csv")

URLS = {"indices": _INDICES_CSV, "sectors": _SECTOR_CSVS,
        "fno": _FNO_CSV}


def available() -> list[str]:
    """Universe keys accepted by load()."""
    keys = list(_INDICES_CSV) + ["indices", "fno", "all_nse"]
    keys += [f"sector:{s}" for s in _SECTOR_CSVS]
    return keys


def sector_names() -> list[str]:
    return list(_SECTOR_CSVS)


def _cache_path(name: str) -> Path:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return CACHE_DIR / f"{slug}.csv"


def _read_cache(path: Path, max_age: dt.timedelta | None):
    if not path.exists():
        return None
    if max_age is not None:
        age = dt.datetime.now() - dt.datetime.fromtimestamp(
            path.stat().st_mtime)
        if age > max_age:
            return None
    rows = path.read_text(encoding="utf-8", errors="ignore")
    return [line for line in rows.splitlines() if line.strip()]


def _write_cache(path: Path, symbols: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(symbols) + "\n", encoding="utf-8")


def _fetch_csv(url: str) -> str:
    import urllib.request
    req = urllib.request.Request(url, headers=_UA)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", "replace")


def _symbols_from_list_csv(text: str) -> list[str]:
    """Constituent CSVs: first row is the header, 'Symbol' column holds
    the NSE symbol."""
    rows = list(csv.DictReader(io.StringIO(text)))
    return sorted({r["Symbol"].strip() for r in rows if r.get("Symbol")})


def _symbols_from_fno_csv(text: str) -> list[str]:
    """F&O market-lots file is comma-separated with no tidy header
    guarantee; the symbol is the first column of data rows after the
    underlining header block."""
    symbols = set()
    for row in csv.reader(io.StringIO(text)):
        if not row:
            continue
        first = row[0].strip().upper()
        if first in ("UNDERLYING", "SYMBOL") or not first:
            continue
        if re.fullmatch(r"[A-Z0-9&\-]+", first):
            symbols.add(first)
    return sorted(symbols)


def _to_yahoo(symbols: list[str]) -> list[str]:
    """NSE symbol -> Yahoo ticker (".NS" suffix; ^-indices unchanged)."""
    return [s if s.startswith("^") else f"{s}.NS" for s in symbols]


def _fetch_symbols(name: str) -> list[str]:
    if name == "indices":
        out: list[str] = []
        for _label, url in _INDICES_CSV.items():
            try:
                out.extend(_symbols_from_list_csv(_fetch_csv(url)))
            except Exception:  # noqa: BLE001 - partial lists still work
                continue
        out.extend(_INDEX_SYMBOLS.values())
        return _to_yahoo(sorted(set(out)))
    if name == "all_nse":
        seen = set()
        for _label, url in _INDICES_CSV.items():
            try:
                seen.update(_symbols_from_list_csv(_fetch_csv(url)))
            except Exception:  # noqa: BLE001
                continue
        return _to_yahoo(sorted(seen))
    if name == "fno":
        return _symbols_from_fno_csv(_fetch_csv(_FNO_CSV))
    if name.startswith("sector:"):
        sector = name.split(":", 1)[1]
        if sector not in _SECTOR_CSVS:
            raise ValueError(f"unknown sector {sector!r}; "
                             f"one of {sorted(_SECTOR_CSVS)}")
        return _to_yahoo(_symbols_from_list_csv(_fetch_csv(_SECTOR_CSVS[sector])))
    if name in _INDICES_CSV:
        return _to_yahoo(_symbols_from_list_csv(_fetch_csv(_INDICES_CSV[name])))
    raise ValueError(f"unknown universe {name!r}; "
                     f"one of {available()}")


def load(name: str, max_age: dt.timedelta | None = CACHE_TTL,
         refresh: bool = False) -> list[str]:
    """Yahoo-finance symbols for a universe, served from the cache when
    fresh.  Raises RuntimeError only when there is neither a fresh
    download nor any cached copy."""
    if name not in _INDICES_CSV and name not in ("indices", "fno",
                                                 "all_nse") \
            and not name.startswith("sector:"):
        raise ValueError(f"unknown universe {name!r}; "
                         f"one of {available()}")
    path = _cache_path(name)
    if not refresh:
        cached = _read_cache(path, max_age)
        if cached is not None:
            return cached
    try:
        symbols = _fetch_symbols(name)
    except Exception as exc:  # noqa: BLE001 - fall back to stale cache
        stale = _read_cache(path, max_age=None)
        if stale is None:
            raise RuntimeError(
                f"could not fetch universe {name!r} ({exc}) and no "
                "cached copy exists") from exc
        return stale
    _write_cache(path, symbols)
    return symbols


def watchlist(text: str) -> list[str]:
    """Free-text watchlist: comma/newline separated NSE symbols."""
    out = []
    for token in re.split(r"[,\n;]+", text or ""):
        token = token.strip().upper()
        if not token:
            continue
        if token.startswith("^"):
            out.append(token)
        else:
            out.append(re.sub(r"\.NS$", "", token) + ".NS")
    return list(dict.fromkeys(out))
