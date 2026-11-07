"""The only Navigator module that touches Postgres."""
from __future__ import annotations

import datetime as dt
import json
import os
from pathlib import Path

import psycopg
from psycopg.types.json import Jsonb

from sbc.navigator.profile import SAMPLE_PROFILE, Profile

MIGRATIONS = Path(__file__).parent / "migrations"


class StoreUnavailable(RuntimeError):
    """Postgres is not configured or not reachable."""


def connect() -> psycopg.Connection:
    url = os.environ.get("NAV_DATABASE_URL", "").strip()
    if not url:
        raise StoreUnavailable("NAV_DATABASE_URL is not set")
    try:
        return psycopg.connect(url, connect_timeout=3)
    except psycopg.ProgrammingError:
        message = "NAV_DATABASE_URL is invalid"
    except psycopg.Error:
        message = "Postgres is unreachable"
    # Raise outside the except block. The psycopg error can echo the URL and
    # password, and `from None` would still keep it on __context__.
    raise StoreUnavailable(message)


def migrate() -> None:
    with connect() as conn:
        for path in sorted(MIGRATIONS.glob("*.sql")):
            conn.execute(path.read_text(encoding="utf8"))


# ---- queries -----------------------------------------------------------------
_ACTIVE = "('queued','running')"
_KEY = ("profile_id", "day", "weights_version", "data_asof", "engine_version", "chart_hash")


def _tx(work):
    """Run work(conn) in one transaction. Any driver error becomes a generic
    StoreUnavailable raised outside the except block, so no driver text (which
    can echo connection details or row values) is kept on the exception chain."""
    failed = False
    try:
        with connect() as conn:
            return work(conn)
    except psycopg.Error:
        failed = True
    if failed:
        raise StoreUnavailable("Postgres query failed")


def _json(value):
    # allow_nan=False: results may hold None, never NaN/Infinity.
    return Jsonb(value, dumps=lambda o: json.dumps(o, allow_nan=False))


def _iso(v):
    return v.isoformat() if isinstance(v, (dt.date, dt.datetime)) else v


def create_profile(p: Profile) -> int:
    return _tx(lambda c: c.execute(
        "insert into natal_profile (label,is_sample,birth_date,birth_time,tz,lat,lon) "
        "values (%s,%s,%s,%s,%s,%s,%s) returning id",
        (p.label, p.is_sample, p.birth_date, p.birth_time, p.tz, p.lat, p.lon)).fetchone()[0])


def get_profile(profile_id: int) -> Profile | None:
    row = _tx(lambda c: c.execute(
        "select label,is_sample,birth_date,birth_time,tz,lat,lon "
        "from natal_profile where id=%s", (profile_id,)).fetchone())
    if row is None:
        return None
    label, is_sample, bdate, btime, tz, lat, lon = row
    return Profile(label=label, is_sample=is_sample, birth_date=bdate.isoformat(),
                   birth_time=btime.strftime("%H:%M:%S"), tz=tz, lat=lat, lon=lon)


def list_profiles() -> list[dict]:
    rows = _tx(lambda c: c.execute(
        "select id,label,is_sample from natal_profile order by id").fetchall())
    return [{"id": i, "label": l, "is_sample": s} for i, l, s in rows]


def ensure_sample() -> int:
    p = SAMPLE_PROFILE

    def work(c):
        c.execute("select pg_advisory_xact_lock(%s)", (80_000_001,))  # serialise first-time inserts
        row = c.execute("select id from natal_profile where is_sample order by id limit 1").fetchone()
        if row:
            return row[0]
        return c.execute(
            "insert into natal_profile (label,is_sample,birth_date,birth_time,tz,lat,lon) "
            "values (%s,%s,%s,%s,%s,%s,%s) returning id",
            (p.label, True, p.birth_date, p.birth_time, p.tz, p.lat, p.lon)).fetchone()[0]

    return _tx(work)


def cached_score(key: dict) -> dict | None:
    row = _tx(lambda c: c.execute(
        "select score,band,action,lineage from daily_score where profile_id=%s and day=%s "
        "and weights_version=%s and data_asof=%s and engine_version=%s and chart_hash=%s",
        tuple(key[k] for k in _KEY)).fetchone())
    if row is None:
        return None
    return {"score": float(row[0]), "band": row[1], "action": row[2], "lineage": row[3]}


def save_score(key: dict, row: dict) -> None:
    _tx(lambda c: c.execute(
        "insert into daily_score (profile_id,day,weights_version,data_asof,engine_version,"
        "chart_hash,score,band,action,lineage) values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) "
        "on conflict (profile_id,day,weights_version,data_asof,engine_version,chart_hash) "
        "do update set score=excluded.score, band=excluded.band, action=excluded.action, "
        "lineage=excluded.lineage",
        (*(key[k] for k in _KEY), row["score"], row["band"], row["action"],
         _json(row["lineage"]))))


def start_run(profile_id: int, meta: dict) -> tuple[int, bool]:
    def work(c):
        for _ in range(3):  # an active run can finish between the insert and the select
            got = c.execute(
                "insert into backtest_run (profile_id,instrument,weights_version,data_asof,"
                "engine_version,chart_hash,status,heartbeat_at,params) "
                "values (%s,%s,%s,%s,%s,%s,'queued',now(),%s) "
                "on conflict (profile_id) where status in ('queued','running') do nothing "
                "returning id",
                (profile_id, meta["instrument"], meta["weights_version"], meta["data_asof"],
                 meta["engine_version"], meta["chart_hash"], _json(meta.get("params", {})))
            ).fetchone()
            if got:
                return got[0], True
            got = c.execute(
                f"select id from backtest_run where profile_id=%s and status in {_ACTIVE}",
                (profile_id,)).fetchone()
            if got:
                return got[0], False
        raise psycopg.Error  # surfaces as StoreUnavailable

    return _tx(work)


def heartbeat(run_id: int) -> None:
    _tx(lambda c: c.execute(
        f"update backtest_run set heartbeat_at=now(), status='running' "
        f"where id=%s and status in {_ACTIVE}", (run_id,)))


def finish_run(run_id: int, results, folds) -> None:
    """Only an active run can finish; a run already expired to failed stays failed."""
    r, f = _json(results), _json(folds)  # NaN raises ValueError here, before any write
    _tx(lambda c: c.execute(
        f"update backtest_run set status='done', results=%s, folds=%s, heartbeat_at=now() "
        f"where id=%s and status in {_ACTIVE}", (r, f, run_id)))


def fail_run(run_id: int, error: str) -> None:
    _tx(lambda c: c.execute(
        f"update backtest_run set status='failed', error=%s where id=%s and status in {_ACTIVE}",
        (str(error)[:500], run_id)))


def get_run(run_id: int) -> dict | None:
    def work(c):
        cur = c.execute(
            "select id,profile_id,instrument,weights_version,data_asof,engine_version,chart_hash,"
            "status,heartbeat_at,error,params,folds,results,created_at "
            "from backtest_run where id=%s", (run_id,))
        row = cur.fetchone()
        return None if row is None else dict(zip([d.name for d in cur.description], row))

    run = _tx(work)
    return None if run is None else {k: _iso(v) for k, v in run.items()}


def expire_stale(seconds: int = 120) -> int:
    return _tx(lambda c: c.execute(
        f"update backtest_run set status='failed', error='run stopped reporting' "
        f"where status in {_ACTIVE} "
        f"and coalesce(heartbeat_at, created_at) < now() - make_interval(secs => %s)",
        (seconds,)).rowcount)
