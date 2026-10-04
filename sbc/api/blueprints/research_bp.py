"""Backtests, futurecasts and the Research Lab.

Moved out of app.py (B-16).
"""

import datetime
from typing import Any
from zoneinfo import ZoneInfo

from flask import Blueprint, Response, current_app, jsonify, request

from sbc.api.errors import internal_error
from sbc.backtest import (
    _bearish_future_score,
    _julian_at_noon,
    run_backtest,
    run_bullish_futurecast,
    run_futurecast,
)
from sbc.config import SECTOR_NAME_MAP
from sbc.engine import (
    _julday,
    _utc_from_local,
)
from sbc.market_events import lunar_phase_event, planetary_aspect_events, planetary_ingress_events
from sbc.nakshatra import (
    tithi_of,
)
from sbc.planets import positions

research_bp = Blueprint('research', __name__)


@research_bp.route("/api/backtest")
def backtest():
    return jsonify(run_backtest())


@research_bp.route("/api/futurecast")
def futurecast():
    center_date = request.args.get("date")
    try:
        if center_date:
            datetime.datetime.strptime(center_date, "%Y-%m-%d")
        return jsonify(run_futurecast(center_date=center_date))
    except ValueError:
        return jsonify({"error": "invalid date"}), 400


@research_bp.route("/api/bullish_futurecast")
def bullish_futurecast():
    center_date = request.args.get("date")
    years = request.args.get("years", type=int, default=1)
    try:
        if center_date:
            datetime.datetime.strptime(center_date, "%Y-%m-%d")
        years = min(max(years, 1), 10)
        return jsonify(run_bullish_futurecast(center_date=center_date, years=years))
    except ValueError:
        return jsonify({"error": "invalid date"}), 400


_crash_series_cache = {}


@research_bp.route("/api/crash_score_series")
def crash_score_series():
    """Daily bearish/crash trigger scores (0-20+) for the NIFTY chart overlay.

    Uses the same _bearish_future_score engine as the Crash Futurecast panel.
    """
    start = request.args.get("start") or ""
    end = request.args.get("end") or ""
    try:
        start_d = datetime.date.fromisoformat(start)
        end_d = datetime.date.fromisoformat(end)
    except (TypeError, ValueError):
        return jsonify({"error": "invalid start/end date"}), 400
    if end_d < start_d:
        return jsonify({"error": "end before start"}), 400
    # Allow up to ~31 months (950 days) to cover 24m history + 6m forecast + buffer
    if (end_d - start_d).days > 950:
        return jsonify({"error": "range too large (max 950 days)"}), 400

    out = []
    d = start_d
    while d <= end_d:
        ds = d.isoformat()
        if ds not in _crash_series_cache:
            try:
                score, reasons, _ = _bearish_future_score(_julian_at_noon(ds))
                _crash_series_cache[ds] = {"date": ds, "score": score,
                                           "reasons": reasons}
            except Exception:
                # Log, and don't cache the failure: the next request retries.
                current_app.logger.exception("crash score failed for %s", ds)
                out.append({"date": ds, "error": "unavailable"})
                d += datetime.timedelta(days=1)
                continue
        out.append(_crash_series_cache[ds])
        d += datetime.timedelta(days=1)
    return jsonify({"series": out})


@research_bp.route("/api/signal/moon", methods=["GET"])
def api_signal_moon():
    try:
        ticker=request.args.get("ticker","^NSEI")
        days=int(request.args.get("days","30"))
        end=datetime.date.today()
        start=end-datetime.timedelta(days=days)
        import pandas as pd
        import yfinance as yf

        from sbc.config import RASHI_TREND
        from sbc.market_data import moon_rashi
        df=yf.download(ticker,start=start,end=end,interval='1d',auto_adjust=True,progress=False)
        if df.empty:
            return jsonify({"error":"no data"}),400
        df.columns=[c[0] if isinstance(c,tuple) else c for c in df.columns]
        df=df[['Close']].dropna()
        ist=ZoneInfo("Asia/Kolkata")
        signals=[]
        for idx in df.index:
            d=pd.to_datetime(idx).date()
            dt=datetime.datetime.combine(d,datetime.time(9,15),tzinfo=ist)
            rashi=moon_rashi(dt)
            trend=RASHI_TREND.get(rashi)
            signals.append({"date":d.isoformat(),"rashi":rashi,"trend":trend,"close":float(df.loc[idx,'Close'])})
        return jsonify({"ticker":ticker,"signals":signals})
    except Exception:
        return internal_error()


@research_bp.route("/api/backtest/walkforward", methods=["GET"])
def api_backtest_walkforward():
    try:
        ticker = request.args.get("ticker","^NSEI")
        window = int(request.args.get("window","365"))
        step = int(request.args.get("step","90"))
        start_str = request.args.get("start")
        end_str = request.args.get("end")
        if start_str:
            start = datetime.date.fromisoformat(start_str)
        else:
            start = datetime.date.today() - datetime.timedelta(days=730)
        if end_str:
            end = datetime.date.fromisoformat(end_str)
        else:
            end = datetime.date.today()
        import pandas as pd
        import yfinance as yf

        from sbc.config import RASHI_TREND
        from sbc.market_data import moon_rashi
        df=yf.download(ticker,start=start,end=end,interval='1d',auto_adjust=True,progress=False)
        if df.empty:
            return jsonify({"error":"no data"}),400
        df.columns=[c[0] if isinstance(c,tuple) else c for c in df.columns]
        df=df[['Close']].dropna()
        ist=ZoneInfo("Asia/Kolkata")
        results=[]
        cur=start
        while cur<end:
            test_end=min(cur+datetime.timedelta(days=window+step), end)
            correct=total=0
            prev=None
            for idx in df.index:
                d=pd.to_datetime(idx).date()
                if d<cur or d>=test_end:
                    continue
                dt=datetime.datetime.combine(d,datetime.time(9,15),tzinfo=ist)
                monday=dt-datetime.timedelta(days=dt.weekday())
                daily=moon_rashi(dt)
                weekly=moon_rashi(datetime.datetime.combine(monday.date(),datetime.time(9,15),tzinfo=ist))
                if RASHI_TREND.get(daily)!=RASHI_TREND.get(weekly):
                    prev=float(df.loc[idx,'Close'])
                    continue
                close=float(df.loc[idx,'Close'])
                if prev is not None:
                    expected=RASHI_TREND[daily]
                    actual="bullish" if close>prev else "bearish" if close<prev else "neutral"
                    if actual!="neutral":
                        total+=1
                        if expected==actual:
                            correct+=1
                prev=close
            acc=correct/total if total else None
            results.append({"train_start":cur.isoformat(),"test_end":test_end.isoformat(),"samples":total,"accuracy":acc})
            cur=cur+datetime.timedelta(days=step)
        return jsonify({"ticker":ticker,"results":results})
    except Exception:
        return internal_error()


def _research_lunar_rows(ticker, start, end, horizon):
    import pandas as pd
    import yfinance as yf

    prices = yf.download(ticker, start=start.isoformat(), end=(end + datetime.timedelta(days=1)).isoformat(),
                         interval="1d", auto_adjust=True, progress=False)
    if prices.empty:
        return []
    if isinstance(prices.columns, pd.MultiIndex):
        prices.columns = [column[0] for column in prices.columns]
    frame = prices[["Open", "High", "Low", "Close"]].dropna()
    frame.index = pd.to_datetime(frame.index).tz_localize(None).normalize()
    rows = []
    for index in range(len(frame) - horizon):
        day = frame.index[index].date()
        utc = _utc_from_local(day.isoformat(), "09:15", "Asia/Kolkata")
        planets, _ = positions(_julday(utc))
        sun = next(planet for planet in planets if planet["name"] == "Sun")
        moon = next(planet for planet in planets if planet["name"] == "Moon")
        tithi = tithi_of(sun["longitude"], moon["longitude"])
        event_record = lunar_phase_event(day, tithi, sun["longitude"], moon["longitude"])
        # Sign ingresses: planets that changed sign vs the previous snapshot
        prev_utc = _utc_from_local((day - datetime.timedelta(days=1)).isoformat(), "09:15", "Asia/Kolkata")
        prev_planets, _ = positions(_julday(prev_utc))
        ingress_records = planetary_ingress_events(day, planets, prev_planets)
        base = float(frame["Close"].iloc[index])
        future = float(frame["Close"].iloc[index + horizon])
        forward = frame.iloc[index + 1:index + horizon + 1]
        daily_returns = frame["Close"].pct_change().iloc[index + 1:index + horizon + 1].dropna()
        trend_window = frame["Close"].iloc[max(0, index - 20):index + 1]
        trend_change = float(trend_window.iloc[-1] / trend_window.iloc[0] - 1) if len(trend_window) > 1 else 0.0
        regime = "bull" if trend_change >= 0.02 else "bear" if trend_change <= -0.02 else "range"
        rows.append({
            "date": day, "weekday": day.weekday(), "base": base,
            "return_pct": (future / base - 1) * 100,
            "event": event_record is not None or bool(ingress_records),
            "event_record": event_record.to_dict() if event_record else None,
            "ingress_record": ingress_records[0].to_dict() if ingress_records else None,
            "volatility_pct": float(daily_returns.std() * 100) if len(daily_returns) > 1 else 0.0,
            "mae_pct": float((forward["Low"].min() / base - 1) * 100) if not forward.empty else 0.0,
            "regime": regime,
        })
    return rows


@research_bp.route("/api/research/event-study", methods=["GET"])
def api_research_event_study():
    """Measure forward returns around lunar phase / ingress events vs all days."""
    ticker = request.args.get("ticker", "^NSEI")
    event = request.args.get("event", "new_moon")
    horizon = min(max(int(request.args.get("horizon", "5")), 1), 20)
    end = datetime.date.fromisoformat(request.args.get("end") or datetime.date.today().isoformat())
    start = datetime.date.fromisoformat(request.args.get("start") or (end - datetime.timedelta(days=3650)).isoformat())
    if event not in {"new_moon", "full_moon", "ingress"} or start >= end:
        return jsonify({"error": "invalid event or date range"}), 400

    try:
        rows = _research_lunar_rows(ticker, start, end, horizon)
        if not rows:
            return jsonify({"error": "no market data available"}), 404
        if event == "ingress":
            event_rows = [row for row in rows if row.get("ingress_record")]
        else:
            event_rows = [row for row in rows
                          if row["event"] and row.get("event_record")
                          and row["event_record"]["event_type"] == event]
        baseline = [row["return_pct"] for row in rows]
        event_returns = [row["return_pct"] for row in event_rows]
        available_controls = [row for row in rows if not row["event"]]
        controls = []
        used_control_dates = set()
        for event_row in event_rows:
            candidates = [row for row in available_controls
                          if row["weekday"] == event_row["weekday"] and row["date"] not in used_control_dates]
            if candidates:
                control = min(candidates, key=lambda row: abs((row["date"] - event_row["date"]).days))
                controls.append(control)
                used_control_dates.add(control["date"])
        control_returns = [row["return_pct"] for row in controls]
        costs_bps = min(max(float(request.args.get("cost_bps", "0")), 0), 1000)
        cost_pct = costs_bps / 100
        net_returns = [value - cost_pct for value in event_returns]
        equity = []
        running = 1.0
        for row, value in zip(event_rows, net_returns):
            running *= 1 + value / 100
            equity.append({"date": row["date"].isoformat(), "value": running})
        control_mean = sum(control_returns) / len(control_returns) if control_returns else 0.0
        import math
        import statistics
        mean = lambda values: sum(values) / len(values) if values else 0.0
        event_mean = mean(event_returns)
        event_std = statistics.stdev(event_returns) if len(event_returns) > 1 else 0.0
        margin = 1.96 * event_std / math.sqrt(len(event_returns)) if event_returns else 0.0
        result: dict[str, Any] = {
            "ticker": ticker, "event": event, "horizon_days": horizon,
            "start": start.isoformat(), "end": end.isoformat(),
            "generated_at": datetime.datetime.now(datetime.UTC).isoformat(),
            "sample_size": len(event_returns), "baseline_sample_size": len(baseline),
            "event_mean_return_pct": event_mean, "event_median_return_pct": statistics.median(event_returns) if event_returns else 0.0,
            "event_stddev_pct": event_std, "event_ci95_low_pct": event_mean - margin, "event_ci95_high_pct": event_mean + margin,
            "baseline_mean_return_pct": mean(baseline),
            "event_win_rate_pct": (sum(value > 0 for value in event_returns) / len(event_returns) * 100) if event_returns else 0.0,
            "baseline_win_rate_pct": (sum(value > 0 for value in baseline) / len(baseline) * 100) if baseline else 0.0,
            "event_returns": [{**row, "date": row["date"].isoformat()} for row in event_rows],
            "matched_control_sample_size": len(control_returns),
            "matched_control_mean_return_pct": control_mean,
            "event_volatility_mean_pct": mean([row["volatility_pct"] for row in event_rows]),
            "baseline_volatility_mean_pct": mean([row["volatility_pct"] for row in rows]),
            "maximum_adverse_excursion_pct": min([row["mae_pct"] for row in event_rows], default=0.0),
            "cost_bps": costs_bps,
            "net_event_mean_return_pct": mean(net_returns),
            "equity_curve": equity,
        }

        # Regime-aware segmentation: bull/bear/range from trend, plus
        # high/low volatility regimes from the median volatility split.
        import statistics as _statistics
        vol_median = _statistics.median([row["volatility_pct"] for row in rows]) if rows else 0.0
        regime_groups: dict = {}
        for row in event_rows:
            trend_regime = row.get("regime", "range")
            vol_regime = "high_vol" if row["volatility_pct"] >= vol_median else "low_vol"
            for key in (trend_regime, vol_regime):
                regime_groups.setdefault(key, []).append(row["return_pct"])
        result["regimes"] = {
            name: {
                "samples": len(values),
                "mean_return_pct": mean(values),
                "win_rate_pct": (sum(value > 0 for value in values) / len(values) * 100) if values else 0.0,
            }
            for name, values in regime_groups.items()
        }
        result["vol_median_pct"] = round(vol_median, 4)
        export_format = request.args.get("format", "json").lower()
        if export_format == "csv":
            import csv
            from io import StringIO
            stream = StringIO()
            fields = ["date", "return_pct", "volatility_pct", "mae_pct", "event", "regime"]
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            for row in result["event_returns"]:
                writer.writerow({key: row.get(key) for key in fields})
            return Response(stream.getvalue(), mimetype="text/csv", headers={"Content-Disposition": "attachment; filename=event-study.csv"})
        if export_format in {"md", "markdown"}:
            from sbc import __version__
            regime_lines = [
                f"  - {name}: n={stats['samples']}, mean={stats['mean_return_pct']:.4f}%, win={stats['win_rate_pct']:.1f}%"
                for name, stats in (result.get("regimes") or {}).items()
            ]
            markdown = "\n".join([
                f"# Event Study: {event}", "", f"- Ticker: `{ticker}`", f"- Window: {horizon} days",
                f"- Sample size: {result['sample_size']}", f"- Matched controls: {result['matched_control_sample_size']}",
                f"- Event mean return: {result['event_mean_return_pct']:.4f}%", f"- Baseline mean return: {result['baseline_mean_return_pct']:.4f}%",
                f"- Event volatility: {result['event_volatility_mean_pct']:.4f}%", f"- Maximum adverse excursion: {result['maximum_adverse_excursion_pct']:.4f}%",
                "", "## Regime segmentation",
                *regime_lines,
                "", "## Assumptions",
                f"- Cost basis: {costs_bps} bps per event; forward window {horizon} trading days",
                "- Controls matched one-to-one by weekday; small samples are not reliable signals",
                "- Source: Swiss Ephemeris (Lahiri) + yfinance daily closes",
                "", f"Generated by SBC Research Lab · calculation version {__version__} · {result['generated_at']}",
            ])
            return Response(markdown, mimetype="text/markdown", headers={"Content-Disposition": "attachment; filename=event-study.md"})
        return jsonify(result)
    except (TypeError, ValueError):
        return jsonify({"error": "invalid research parameters"}), 400
    except Exception:
        current_app.logger.exception("Event study failed")
        return jsonify({"error": "event study unavailable"}), 500


@research_bp.route("/api/research/aspects", methods=["GET"])
def api_research_aspects():
    """Return filtered planetary aspect events with market response metrics."""
    ticker = request.args.get("ticker", "^NSEI")
    start = datetime.date.fromisoformat(request.args.get("start") or (datetime.date.today() - datetime.timedelta(days=3650)).isoformat())
    end = datetime.date.fromisoformat(request.args.get("end") or datetime.date.today().isoformat())
    horizon = min(max(int(request.args.get("horizon", "5")), 1), 20)
    planet_a = request.args.get("planet_a") or None
    planet_b = request.args.get("planet_b") or None
    aspect = request.args.get("aspect") or None
    try:
        max_orb = float(request.args.get("max_orb", "8"))
    except ValueError:
        return jsonify({"error": "invalid max_orb"}), 400
    max_orb = max(0.0, min(8.0, max_orb))
    try:
        import pandas as pd
        import yfinance as yf
        prices = yf.download(ticker, start=start.isoformat(), end=(end + datetime.timedelta(days=1)).isoformat(), interval="1d", auto_adjust=True, progress=False)
        if prices.empty:
            return jsonify({"error": "no market data available"}), 404
        if isinstance(prices.columns, pd.MultiIndex):
            prices.columns = [column[0] for column in prices.columns]
        close = prices["Close"].dropna()
        close.index = pd.to_datetime(close.index).tz_localize(None).normalize()
        events = []
        prev_planets = None
        for index in range(len(close) - horizon):
            day = close.index[index].date()
            planets, _ = positions(_julday(_utc_from_local(day.isoformat(), "09:15", "Asia/Kolkata")))
            matches = planetary_aspect_events(day, planets, prev_planets)
            prev_planets = planets
            for event_record in matches:
                event_name = event_record.metadata.get("aspect")
                pair = {event_record.planet_a, event_record.planet_b}
                if aspect and event_name != aspect:
                    continue
                if planet_a and planet_a not in pair:
                    continue
                if planet_b and planet_b not in pair:
                    continue
                if event_record.metadata.get("orb") is not None and max_orb is not None \
                        and event_record.metadata["orb"] > max_orb:
                    continue
                base = float(close.iloc[index])
                future = float(close.iloc[index + horizon])
                events.append({**event_record.to_dict(), "return_pct": (future / base - 1) * 100})
        grouped: dict = {}
        for rec in events:
            key = (rec["planet_a"], rec["planet_b"],
                   rec["metadata"]["aspect"], rec["metadata"].get("state"))
            grouped.setdefault(key, []).append(rec["return_pct"])
        rows = [{"planet_a": key[0], "planet_b": key[1], "aspect": key[2], "state": key[3],
                 "samples": len(values),
                 "mean_return_pct": sum(values) / len(values),
                 "win_rate_pct": sum(value > 0 for value in values) / len(values) * 100}
                for key, values in grouped.items()]
        return jsonify({"ticker": ticker, "horizon_days": horizon, "start": start.isoformat(), "end": end.isoformat(),
                        "filters": {"planet_a": planet_a, "planet_b": planet_b, "aspect": aspect,
                                    "max_orb": max_orb},
                        "events": events, "groups": rows,
                        "generated_at": datetime.datetime.now(datetime.UTC).isoformat()})
    except (TypeError, ValueError):
        return jsonify({"error": "invalid aspect research parameters"}), 400
    except Exception:
        current_app.logger.exception("Aspect research failed")
        return jsonify({"error": "aspect research unavailable"}), 500


@research_bp.route("/api/research/cycles", methods=["GET"])
def api_research_cycles():
    """Return daily solar/lunar cycle observations + Bradley barometer (experimental)."""
    start = datetime.date.fromisoformat(request.args.get("start") or (datetime.date.today() - datetime.timedelta(days=365)).isoformat())
    end = datetime.date.fromisoformat(request.args.get("end") or datetime.date.today().isoformat())
    ticker = request.args.get("ticker") or None
    horizon = min(max(int(request.args.get("horizon", "5")), 1), 20)
    rows = []
    day = start
    from sbc.bradley import bradley_score, forward_return_validation, turning_point_candidates
    while day <= end:
        planets, _ = positions(_julday(_utc_from_local(day.isoformat(), "09:15", "Asia/Kolkata")))
        sun = next(planet for planet in planets if planet["name"] == "Sun")
        moon = next(planet for planet in planets if planet["name"] == "Moon")
        separation = (moon["longitude"] - sun["longitude"]) % 360
        phase = "new_moon" if separation < 12 or separation >= 348 else "full_moon" if 168 <= separation <= 192 else "waxing" if separation < 180 else "waning"
        rows.append({"date": day.isoformat(), "sun_sign": sun["sign"], "moon_sign": moon["sign"],
                     "sun_moon_angle": round(separation, 2), "phase": phase,
                     "bradley_score": bradley_score(planets)})
        day += datetime.timedelta(days=1)

    candidates = turning_point_candidates(rows)

    validation = None
    if ticker:
        try:
            import pandas as pd
            import yfinance as yf
            prices = yf.download(ticker, start=start.isoformat(), end=(end + datetime.timedelta(days=1)).isoformat(),
                                 interval="1d", auto_adjust=True, progress=False)
            if not prices.empty:
                if isinstance(prices.columns, pd.MultiIndex):
                    prices.columns = [column[0] for column in prices.columns]
                close = prices["Close"].dropna()
                close.index = pd.to_datetime(close.index).tz_localize(None).normalize()
                closes_by_date = {d.date().isoformat(): float(v) for d, v in close.items()}
                validation = forward_return_validation(rows, closes_by_date, horizon)
        except Exception:
            current_app.logger.exception("Bradley validation failed")

    return jsonify({"start": start.isoformat(), "end": end.isoformat(), "experimental": True,
                    "rows": rows, "turning_point_candidates": candidates,
                    "validation": validation,
                    "generated_at": datetime.datetime.now(datetime.UTC).isoformat()})


@research_bp.route("/api/research/walk-forward", methods=["GET"])
def api_research_walk_forward():
    """Run rolling train/test lunar-event studies without mixing test data."""
    ticker = request.args.get("ticker", "^NSEI")
    event = request.args.get("event", "new_moon")
    horizon = min(max(int(request.args.get("horizon", "5")), 1), 20)
    train_days = min(max(int(request.args.get("train_days", "730")), 90), 3650)
    test_days = min(max(int(request.args.get("test_days", "180")), 30), 730)
    step_days = min(max(int(request.args.get("step_days", "180")), 30), 730)
    end = datetime.date.fromisoformat(request.args.get("end") or datetime.date.today().isoformat())
    requested_start = request.args.get("start")
    start = datetime.date.fromisoformat(requested_start) if requested_start else end - datetime.timedelta(days=3650)
    if event not in {"new_moon", "full_moon"} or start >= end:
        return jsonify({"error": "invalid event or date range"}), 400

    try:
        costs_bps = min(max(float(request.args.get("cost_bps", "0")), 0), 1000)
        rows = _research_lunar_rows(ticker, start, end, horizon)
        if not rows:
            return jsonify({"error": "no market data available"}), 404

        def in_range(row, lower, upper):
            return lower <= row["date"] < upper

        def metrics(sample):
            events = [row["return_pct"] - costs_bps / 100 for row in sample if row["event"] and row["event_record"]["event_type"] == event]
            baseline = [row["return_pct"] for row in sample]
            return {
                "event_samples": len(events),
                "baseline_samples": len(baseline),
                "event_mean_return_pct": sum(events) / len(events) if events else None,
                "baseline_mean_return_pct": sum(baseline) / len(baseline) if baseline else None,
                "event_win_rate_pct": sum(value > 0 for value in events) / len(events) * 100 if events else None,
                "event_mean_return_net_pct": sum(events) / len(events) if events else None,
            }

        folds = []
        training_start = start
        test_start = training_start + datetime.timedelta(days=train_days)
        while test_start < end:
            train_end = test_start
            test_end = min(test_start + datetime.timedelta(days=test_days), end)
            train = [row for row in rows if in_range(row, training_start, train_end)]
            test = [row for row in rows if in_range(row, test_start, test_end)]
            folds.append({
                "train_start": start.isoformat(), "train_end": train_end.isoformat(),
                "test_start": test_start.isoformat(), "test_end": test_end.isoformat(),
                "train": metrics(train), "test": metrics(test),
            })
            test_start += datetime.timedelta(days=step_days)

        test_events = []
        test_baseline = []
        for row in rows:
            date_key = row["date"].isoformat()
            if any(fold["test_start"] <= date_key < fold["test_end"] for fold in folds):
                test_baseline.append(row)
                if row["event"] and row["event_record"]["event_type"] == event:
                    test_events.append(row)
        regime_results = {}
        for regime_name in ("bull", "bear", "range"):
            regime_rows = [row for row in test_baseline if row["regime"] == regime_name]
            regime_results[regime_name] = metrics(regime_rows)
        gross_fold_means = [fold["test"]["event_mean_return_pct"] for fold in folds if fold["test"]["event_mean_return_pct"] is not None]
        accuracy_decay = (gross_fold_means[-1] - gross_fold_means[0]) if len(gross_fold_means) > 1 else None
        aggregate = {
            "event_samples": len(test_events),
            "baseline_samples": len(test_baseline),
            "event_mean_return_pct": sum(row["return_pct"] for row in test_events) / len(test_events) if test_events else None,
            "baseline_mean_return_pct": sum(row["return_pct"] for row in test_baseline) / len(test_baseline) if test_baseline else None,
            "event_win_rate_pct": sum(row["return_pct"] > 0 for row in test_events) / len(test_events) * 100 if test_events else None,
            "event_mean_return_net_pct": sum(row["return_pct"] - costs_bps / 100 for row in test_events) / len(test_events) if test_events else None,
            "cost_bps": costs_bps,
            "regime_results": regime_results,
            "accuracy_decay_pct_points": accuracy_decay,
        }
        return jsonify({
            "ticker": ticker, "event": event, "horizon_days": horizon,
            "train_days": train_days, "test_days": test_days, "step_days": step_days,
            "start": requested_start or (end - datetime.timedelta(days=3650)).isoformat(), "end": end.isoformat(),
            "generated_at": datetime.datetime.now(datetime.UTC).isoformat(),
            "folds": folds, "aggregate_test": aggregate,
        })
    except (TypeError, ValueError):
        return jsonify({"error": "invalid walk-forward parameters"}), 400
    except Exception:
        current_app.logger.exception("Research walk-forward failed")
        return jsonify({"error": "walk-forward study unavailable"}), 500


@research_bp.route("/api/backtest/moon", methods=["GET"])
def api_backtest_moon():
    try:
        ticker = request.args.get("ticker", "^NSEI")
        start_str = request.args.get("start")
        end_str = request.args.get("end")
        multi_tf = request.args.get("multi_tf", "true").lower() == "true"
        regime = request.args.get("regime", "false").lower() == "true"
        volume = request.args.get("volume", "false").lower() == "true"
        vedha = request.args.get("vedha", "false").lower() == "true"
        if start_str:
            start = datetime.date.fromisoformat(start_str)
        else:
            start = datetime.date.today() - datetime.timedelta(days=730)
        if end_str:
            end = datetime.date.fromisoformat(end_str)
        else:
            end = datetime.date.today()
        # Import backtest engine logic inline
        import pandas as pd
        import yfinance as yf

        from sbc.config import RASHI_TREND
        from sbc.market_data import moon_rashi
        df=yf.download(ticker,start=start,end=end,interval='1d',auto_adjust=True,progress=False)
        if df.empty:
            return jsonify({"error":"no data"}),400
        df.columns=[c[0] if isinstance(c,tuple) else c for c in df.columns]
        df=df[['Open','High','Low','Close','Volume']].dropna()
        df['vol_ma']=df['Volume'].rolling(20).mean()
        ist=ZoneInfo("Asia/Kolkata")
        correct=total=0
        results=[]
        # vedha cache
        vedha_cache={}
        sector_name=SECTOR_NAME_MAP.get(ticker, "Nifty Large Caps")
        for i in range(1,len(df)-1):
            d=pd.to_datetime(df.index[i]).date()
            dt=datetime.datetime.combine(d,datetime.time(9,15),tzinfo=ist)
            daily_rashi=moon_rashi(dt)
            expected=RASHI_TREND.get(daily_rashi)
            if expected is None:
                continue
            if multi_tf:
                monday=dt-datetime.timedelta(days=dt.weekday())
                weekly=moon_rashi(datetime.datetime.combine(monday.date(),datetime.time(9,15),tzinfo=ist))
                if RASHI_TREND.get(weekly)!=expected:
                    continue
            if regime and d.day in [1,15]:
                continue
            if vedha:
                y,m=d.year,d.month
                key=(y,m)
                if key not in vedha_cache:
                    import calendar

                    from sbc.monthly_heatmap import monthly_heatmap
                    start_m=datetime.date(y,m,1)
                    days=calendar.monthrange(y,m)[1]+5
                    res=monthly_heatmap(start_date=start_m, days=days, tz_name='Asia/Kolkata', anchor_key='nse')
                    mat=res.get('matrix',{})
                    scores={}
                    if sector_name in mat:
                        for dd,s in mat[sector_name].items():
                            try: scores[dd]=float(s)
                            except (TypeError, ValueError): pass
                    vedha_cache[key]=scores
                v=vedha_cache[key].get(d.isoformat())
                if v is not None and (
                        (expected=="bullish" and v<=0) or (expected=="bearish" and v>=0)):
                    continue
            entry_i=i+1
            if volume:
                if pd.isna(df['vol_ma'].iloc[entry_i]): continue
                if df['Volume'].iloc[entry_i] < df['vol_ma'].iloc[entry_i]: continue
                open_p=float(df['Open'].iloc[entry_i])
                prev_close=float(df['Close'].iloc[i])
                if expected=="bullish" and open_p<=prev_close: continue
                if expected=="bearish" and open_p>=prev_close: continue
            prev_close=float(df['Close'].iloc[i])
            close_next=float(df['Close'].iloc[entry_i])
            actual="bullish" if close_next>prev_close else "bearish" if close_next<prev_close else "neutral"
            if actual!="neutral":
                total+=1
                match=expected==actual
                if match: correct+=1
                results.append({"date":d.isoformat(),"expected":expected,"actual":actual,"match":bool(match)})
        acc=correct/total if total else 0
        return jsonify({"ticker":ticker,"samples":total,"correct":correct,"accuracy":acc,"results":results})
    except Exception:
        return internal_error()

