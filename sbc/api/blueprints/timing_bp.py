"""Chart & Timing extras: nakshatra/astro plots, Gann precision, astro cycles, expiry range, prices, daily confluence, Rahu/Ketu traps.

Moved out of app.py (B-16).
"""

import datetime
import time
from io import BytesIO
from zoneinfo import ZoneInfo

from flask import Blueprint, current_app, jsonify, request, send_file

from sbc.api.errors import internal_error
from sbc.astro_plot import generate_astro_plot, serialize_plot_data
from sbc.engine import (
    build_response,
)
from sbc.market_data import get_nifty_ohlc
from sbc.sector_keywords import keywords_for

timing_bp = Blueprint('timing', __name__)


@timing_bp.route("/api/nakshatra_chart")
def nakshatra_chart():
    """Render a native Python NIFTY chart with the selected forecast bias."""
    date_str = request.args.get("date") or datetime.date.today().isoformat()
    try:
        center = datetime.date.fromisoformat(date_str)
        months = min(max(int(request.args.get("months", "3")), 1), 12)
    except (TypeError, ValueError):
        return jsonify({"error": "invalid date or chart range"}), 400

    start = center - datetime.timedelta(days=months * 31)
    candles = get_nifty_ohlc(start.isoformat(), center.isoformat())
    if not candles:
        return jsonify({"error": "NIFTY price data is unavailable"}), 503

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.dates as mdates
        import matplotlib.pyplot as plt
        import pandas as pd

        frame = pd.DataFrame(candles)
        frame["date"] = pd.to_datetime(frame["time"])
        selected = build_response(date_str, "09:15", "Asia/Kolkata", "nifty", "allthree")
        score = float(selected.get("net", 0))
        verdict = selected.get("sentiment", {}).get("verdict", "NEUTRAL")

        fig, ax = plt.subplots(figsize=(12, 5.5), dpi=140)
        fig.patch.set_facecolor("#0b1220")
        ax.set_facecolor("#111a2e")
        ax.plot(frame["date"], frame["close"], color="#fbbf24", linewidth=1.8, label="NIFTY 50 close")
        ax.fill_between(frame["date"], frame["low"], frame["high"], color="#fbbf24", alpha=0.08, label="Daily range")
        ax.axvline(pd.Timestamp(center), color="#38bdf8", linestyle="--", linewidth=1, label="Forecast date")
        color = "#34d399" if score > 0 else "#f87171" if score < 0 else "#94a3b8"
        ax.scatter([pd.Timestamp(center)], [frame["close"].iloc[-1]], color=color, s=70, zorder=4)
        ax.annotate(f"{verdict}  {score:+.2f}", (pd.Timestamp(center), frame["close"].iloc[-1]),
                    xytext=(10, 12), textcoords="offset points", color=color, fontsize=9,
                    bbox={"boxstyle": "round,pad=0.3", "fc": "#0b1220", "ec": color, "alpha": 0.9})
        ax.set_title(f"NIFTY 50 · Daily Nakshatra + SBC Confluence · {center.isoformat()}", color="#f8fafc", loc="left", pad=14)
        ax.set_ylabel("Index level", color="#94a3b8")
        ax.grid(True, color="#334155", alpha=0.35)
        ax.tick_params(colors="#cbd5e1")
        for spine in ax.spines.values():
            spine.set_color("#334155")
        ax.xaxis.set_major_locator(mdates.AutoDateLocator())
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
        fig.autofmt_xdate()
        ax.legend(facecolor="#111a2e", edgecolor="#334155", labelcolor="#e2e8f0", loc="upper left")
        fig.tight_layout()
        output = BytesIO()
        fig.savefig(output, format="png", facecolor=fig.get_facecolor(), bbox_inches="tight")
        plt.close(fig)
        output.seek(0)
        return send_file(output, mimetype="image/png", max_age=0)
    except Exception:
        current_app.logger.exception("Native Nakshatra chart failed")
        return jsonify({"error": "native chart generation failed"}), 500


@timing_bp.route("/api/rahu_ketu_trap_calendar")
def rahu_ketu_trap_calendar():
    """Industry-wise daily Rahu/Ketu trap calendar."""
    start = request.args.get("start")
    end = request.args.get("end")
    industries = request.args.get("industries")
    try:
        if not start or not end:
            return jsonify({"error": "start and end required"}), 400
        datetime.date.fromisoformat(start)
        datetime.date.fromisoformat(end)
    except ValueError:
        return jsonify({"error": "invalid date"}), 400
    industries_list = None
    if industries:
        industries_list = [i.strip() for i in industries.split(",")]
    from sbc.rahu_ketu_trap import generate_calendar
    result = generate_calendar(start, end, industries_list)
    return jsonify(result)


@timing_bp.route("/api/astro_plot")
def astro_plot():
    center_date = request.args.get("date") or datetime.date.today().isoformat()
    window_days = request.args.get("window", 30, type=int)
    resolution = request.args.get("resolution", "daily")
    timezone = request.args.get("tz", "Asia/Kolkata")
    latitude = request.args.get("lat", 19.0760, type=float)
    longitude = request.args.get("lon", 72.8777, type=float)
    house_system = request.args.get("house_system", "whole_sign")

    try:
        datetime.datetime.strptime(center_date, "%Y-%m-%d")
    except ValueError:
        return jsonify({"error": "invalid date"}), 400

    if resolution not in ("daily", "hourly"):
        return jsonify({"error": "resolution must be 'daily' or 'hourly'"}), 400

    if house_system not in ("whole_sign", "placidus", "equal", "koch", "regiomontanus", "campanus"):
        return jsonify({"error": "invalid house system"}), 400

    window_days = max(1, min(window_days, 180))

    plot_data = generate_astro_plot(
        center_date=center_date,
        window_days=window_days,
        resolution=resolution,
        timezone=timezone,
        latitude=latitude,
        longitude=longitude,
        house_system=house_system,
    )

    return jsonify(serialize_plot_data(plot_data))


@timing_bp.route("/api/price", methods=["GET"])
def api_price():
    try:
        import pandas as pd
        import yfinance as yf
        ticker = request.args.get("ticker","^NSEBANK")
        days = request.args.get("days")
        start_str = request.args.get("start")
        end_str = request.args.get("end")
        interval = request.args.get("interval","1d")
        if start_str and end_str:
            start = datetime.date.fromisoformat(start_str)
            end = datetime.date.fromisoformat(end_str) + datetime.timedelta(days=1)
        elif days:
            end = datetime.date.today()
            start = end - datetime.timedelta(days=int(days))
        else:
            end = datetime.date.today()
            start = end - datetime.timedelta(days=180)
        # Server-side fallback map
        fallback_map = {
            '^CNXIT':None,
            '^CNXAUTO':None,
            '^CNXMETAL':None,
            '^CNXFMCG':None,
            '^CNXPHARMA':None,
            '^CNXENERGY':None,
            '^CNXREALTY':None
        }
        df = yf.download(ticker, start=start, end=end, interval=interval, auto_adjust=True, progress=False)
        if df.empty:
            fb = fallback_map.get(ticker)
            if fb:
                df = yf.download(fb, start=start, end=end, interval='1d', auto_adjust=True, progress=False)
        if df.empty:
            return jsonify([])
        # yfinance may return MultiIndex columns; flatten
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = ['_'.join([str(c) for c in col if str(c)!='']).strip('_') for col in df.columns.values]
        # pick first Open/High/Low/Close columns
        col_map = {}
        for c in df.columns:
            if 'Open' in c: col_map['Open']=c
            if 'High' in c: col_map['High']=c
            if 'Low' in c: col_map['Low']=c
            if 'Close' in c: col_map['Close']=c
        candles = []
        for idx,row in df.iterrows():
            try:
                candles.append({
                    "time": int(pd.to_datetime(idx).timestamp()),
                    "open": float(row[col_map.get('Open','Open')]),
                    "high": float(row[col_map.get('High','High')]),
                    "low": float(row[col_map.get('Low','Low')]),
                    "close": float(row[col_map.get('Close','Close')])
                })
            except Exception:
                continue
        resp = jsonify(candles)
        if candles and interval == "1d":
            from sbc import data_freshness
            # Daily bars are stamped at local midnight; read the date in IST.
            last = datetime.datetime.fromtimestamp(candles[-1]["time"], ZoneInfo("Asia/Kolkata")).date()
            fresh = data_freshness.stamp(last)
            resp.headers["X-Data-As-Of"] = fresh["as_of"]
            resp.headers["X-Data-Stale"] = "1" if fresh["stale"] else "0"
            resp.headers["X-Data-Expected"] = fresh["expected"]
            resp.headers["X-Data-Sessions-Behind"] = str(fresh["sessions_behind"])
        return resp
    except Exception:
        return internal_error()


_daily_confluence_cache: dict = {}


@timing_bp.route("/api/daily_confluence", methods=["GET"])
def api_daily_confluence():
    """Return one compact daily confluence result and its forward forecast."""
    date_str = request.args.get("date")
    try:
        start = datetime.date.fromisoformat(date_str) if date_str else datetime.date.today()
        days = min(max(int(request.args.get("days", "7")), 1), 14)
    except (TypeError, ValueError):
        return jsonify({"error": "invalid date or days"}), 400

    cache_key = (start.isoformat(), days)
    cached = _daily_confluence_cache.get(cache_key)
    if cached:
        payload = {key: value for key, value in cached.items() if key != "_cached_at"}
        payload["cache"] = {"hit": True, "age_seconds": max(0, int(time.time() - cached["_cached_at"]))}
        return jsonify(payload)

    forecast = []
    try:
        for offset in range(days):
            day = start + datetime.timedelta(days=offset)
            result = build_response(day.isoformat(), "09:15", "Asia/Kolkata", "nifty", "allthree")
            moon: dict = next((planet for planet in result["planets"] if planet["name"] == "Moon"), {})
            net = float(result.get("net", 0))
            nakshatra = moon.get("nakshatra", "Unknown")
            forecast.append({
                "date": day.isoformat(),
                "nakshatra": nakshatra,
                "keywords": keywords_for(nakshatra),
                "vedha_net": net,
                "direction": "Bullish" if net > 0 else "Bearish" if net < 0 else "Neutral",
            })
        current = forecast[0]
        payload = {
            "date": start.isoformat(),
            "moon_nakshatra": current["nakshatra"],
            "keywords": current["keywords"],
            "vedha_net": current["vedha_net"],
            "direction": current["direction"],
            "forecast": forecast,
            "generated_at": datetime.datetime.now(datetime.UTC).isoformat(),
            "calculation_version": "daily-confluence-v3",
            "data_source": "Swiss Ephemeris",
            "cache": {"hit": False, "age_seconds": 0},
        }
        _daily_confluence_cache[cache_key] = {**payload, "_cached_at": time.time()}
        return jsonify(payload)
    except Exception:
        current_app.logger.exception("Daily confluence generation failed")
        return jsonify({"error": "daily confluence unavailable"}), 500


@timing_bp.route("/api/gann/precision", methods=["GET"])
def api_gann_precision():
    try:
        ticker = request.args.get("ticker","^NSEI")
        days = int(request.args.get("days","90"))
        asset_type = request.args.get("asset_type","indices")
        from sbc.gann_zones import GANN_ASSET_TICKS, classify_gann_zones
        if asset_type not in GANN_ASSET_TICKS:
            return jsonify({"error":"unknown asset_type (stocks/indices/commodities)"}),400
        end = datetime.date.today()
        start = end - datetime.timedelta(days=days)
        import yfinance as yf
        df = yf.download(ticker, start=start, end=end, interval='1d', auto_adjust=True, progress=False)
        if df.empty:
            return jsonify({"error":"no data"}),400
        df.columns = [c[0] if isinstance(c,tuple) else c for c in df.columns]
        high = float(df['High'].max())
        low = float(df['Low'].min())
        close = float(df['Close'].iloc[-1])
        range_ = high - low
        zones, levels, _ = classify_gann_zones(high, low, close, asset_type)
        return jsonify({
            "ticker":ticker,
            "asset_type":asset_type,
            "high":high,
            "low":low,
            "close":close,
            "range":range_,
            "levels":levels,
            "zones":zones,
        })
    except Exception:
        return internal_error()


# ticker -> (monotonic time of last attempt, last close or None). A failed
# lookup is cached too, so a rate-limited yfinance isn't re-hit on every click.
_ref_price_cache: dict[str, tuple[float, float | None]] = {}
_REF_PRICE_TTL_S = 10 * 60


def _ref_price(ticker):
    """Latest daily close for ticker, cached; None when unavailable."""
    now = time.monotonic()
    hit = _ref_price_cache.get(ticker)
    if hit and now - hit[0] < _REF_PRICE_TTL_S:
        return hit[1]
    price = None
    try:
        import yfinance as yf
        df = yf.download(ticker, period="5d", interval="1d", auto_adjust=True, progress=False)
        if not df.empty:
            df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
            price = float(df["Close"].iloc[-1])
    except Exception:
        price = None
    _ref_price_cache[ticker] = (now, price)
    return price


@timing_bp.route("/api/astro/cycles", methods=["GET"])
def api_astro_cycles():
    """AstroCycle Pro: Mercury/Moon cycle time bars + Moon nakshatra ingresses."""
    try:
        date_str = request.args.get("date") or datetime.date.today().isoformat()
        datetime.date.fromisoformat(date_str)
        tz_name = request.args.get("tz", "Asia/Kolkata")
        ticker = request.args.get("ticker", "^NSEI")
        try:
            sl_points = float(request.args.get("sl_points", "15"))
        except ValueError:
            return jsonify({"error": "invalid sl_points"}), 400

        ref_price = _ref_price(ticker)

        from sbc.astro_cycles import cycle_bars, moon_ingress_bars
        bars = cycle_bars(date_str, tz_name, ref_price=ref_price, sl_points=sl_points)
        ingresses = moon_ingress_bars(date_str, tz_name)
        return jsonify({
            "date": date_str,
            "tz": tz_name,
            "ticker": ticker,
            "ref_price": ref_price,
            "sl_points": sl_points,
            "bars": bars,
            "moon_ingresses": ingresses,
            "method": "Mercury/Moon planetary horas (Chaldean weekday sequence) + Moon nakshatra ingresses; market hours 09:15-15:30 IST.",
            "disclaimer": "Research astro-timing, not investment advice.",
        })
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception:
        return internal_error()


@timing_bp.route("/api/expiry/range", methods=["GET"])
def api_expiry_range():
    """Expiry Range Indicator: forecast expiry-day support/resistance."""
    try:
        instrument = request.args.get("instrument", "NIFTY")
        date_str = request.args.get("date") or datetime.date.today().isoformat()
        datetime.date.fromisoformat(date_str)
        try:
            buffer_pct = float(request.args.get("buffer_pct", "0.0025"))
        except ValueError:
            return jsonify({"error": "invalid buffer_pct"}), 400
        from_date = datetime.date.fromisoformat(date_str)
        from sbc.expiry_range import expiry_range_levels, next_expiry
        expiry = next_expiry(instrument, from_date)
        ticker = "^NSEI" if instrument.upper().replace(" ", "") == "NIFTY" else "^NSEBANK"
        import yfinance as yf
        start = expiry - datetime.timedelta(days=10)
        df = yf.download(ticker, start=start, end=expiry + datetime.timedelta(days=1),
                         interval="1d", auto_adjust=True, progress=False)
        if df.empty:
            return jsonify({"error": "no price data"}), 400
        df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
        dates = [idx.date() if hasattr(idx, "date") else None for idx in df.index]
        ref_idx = next((i for i, d in enumerate(dates) if d and d >= expiry), None)
        prev_idx = ref_idx - 1 if ref_idx is not None else len(dates) - 2
        if prev_idx is None or prev_idx < 0:
            return jsonify({"error": "no reference day before expiry"}), 400
        ref = df.iloc[prev_idx]
        ohlc = {"open": float(ref["Open"]), "high": float(ref["High"]),
                "low": float(ref["Low"]), "close": float(ref["Close"])}
        levels = expiry_range_levels(ohlc, buffer_pct)
        return jsonify({
            "instrument": instrument.upper().replace(" ", ""),
            "expiry": expiry.isoformat(),
            "levels": levels,
            "method": "Floor-trader pivots from previous trading day OHLC with 0.25% false-breakout buffer.",
            "disclaimer": "Research forecast, not investment advice.",
        })
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception:
        return internal_error()


@timing_bp.route("/api/expiry/backtest", methods=["GET"])
def api_expiry_backtest():
    """Expiry Range Indicator backtest: containment and false-breakout rates."""
    try:
        instrument = request.args.get("instrument", "NIFTY")
        try:
            months = int(request.args.get("months", "3"))
        except ValueError:
            return jsonify({"error": "invalid months"}), 400
        try:
            buffer_pct = float(request.args.get("buffer_pct", "0.0025"))
        except ValueError:
            return jsonify({"error": "invalid buffer_pct"}), 400
        from sbc.expiry_range import backtest_expiry
        result = backtest_expiry(instrument, months, buffer_pct)
        return jsonify(result), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception:
        return internal_error()

