"""Backtests, futurecasts and the Research Lab.

Moved out of app.py (B-16).
"""

import datetime
from zoneinfo import ZoneInfo

from flask import Blueprint, current_app, jsonify, request

from sbc.api.errors import internal_error
from sbc.backtest import (
    _bearish_future_score,
    _julian_at_noon,
    run_backtest,
    run_bullish_futurecast,
    run_futurecast,
)
from sbc.config import SECTOR_NAME_MAP

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


# Trading Signals panel: Moon-sign signal check (repurposed from /api/backtest/moon).
_SIGNAL_SYMBOLS = {
    "NIFTY": ("NIFTY 50", None), "SENSEX": ("SENSEX", None),
    "NIFTYBANK": ("Nifty Bank", "^NSEBANK"), "NIFTYIT": ("Nifty IT", "^CNXIT"),
    "NIFTYAUTO": ("Nifty Auto", "^CNXAUTO"), "NIFTYMETAL": ("Nifty Metal", "^CNXMETAL"),
    "NIFTYFMCG": ("Nifty FMCG", "^CNXFMCG"), "NIFTYPHARMA": ("Nifty Pharma", "^CNXPHARMA"),
    "NIFTYENERGY": ("Nifty Energy", "^CNXENERGY"), "NIFTYREALTY": ("Nifty Realty", "^CNXREALTY"),
}


def _signal_bars(symbol: str, start: datetime.date, end: datetime.date) -> tuple[list[dict], str]:
    """NIFTY and SENSEX from market.db (offline); sector indices from Yahoo."""
    name, ticker = _SIGNAL_SYMBOLS[symbol]
    if ticker is None:
        from sbc import market_store
        return market_store.get_daily(symbol, start.isoformat(), end.isoformat()), "market.db"
    import yfinance as yf
    df = yf.download(ticker, start=start, end=end + datetime.timedelta(days=1), interval="1d",
                     auto_adjust=True, progress=False)
    if df.empty:
        return [], f"Yahoo ({ticker})"
    df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
    df = df[["Open", "High", "Low", "Close"]].dropna()
    bars = [{"date": idx.date().isoformat(), "open": float(r.Open), "high": float(r.High),
             "low": float(r.Low), "close": float(r.Close)} for idx, r in df.iterrows()]
    return bars, f"Yahoo ({ticker})"


@research_bp.route("/api/signals/moon-check", methods=["GET"])
def api_signals_moon_check():
    """?symbol=NIFTY&years=2&multi_tf=true&regime=false&gap=false"""
    from sbc.moon_signal_check import check
    symbol = (request.args.get("symbol") or "NIFTY").upper()
    if symbol not in _SIGNAL_SYMBOLS:
        return jsonify({"error": f"symbol must be one of {', '.join(_SIGNAL_SYMBOLS)}"}), 400
    try:
        years = max(1, min(10, int(request.args.get("years", "2"))))
    except ValueError:
        return jsonify({"error": "years must be 1-10"}), 400
    flag = lambda k, d: (request.args.get(k, d).lower() == "true")  # noqa: E731
    end = datetime.date.today()
    start = end - datetime.timedelta(days=365 * years)
    try:
        bars, source = _signal_bars(symbol, start, end)
    except Exception:
        current_app.logger.exception("moon-check data load failed")
        return jsonify({"error": "price data unavailable for this symbol right now"}), 503
    if len(bars) < 30:
        return jsonify({"error": f"not enough price history from {source}"}), 404
    out = check(bars, multi_tf=flag("multi_tf", "true"), regime=flag("regime", "false"),
                gap_filter=flag("gap", "false"))
    return jsonify({"symbol": symbol, "name": _SIGNAL_SYMBOLS[symbol][0], "source": source,
                    "start": bars[0]["date"], "end": bars[-1]["date"],
                    "bars": [{k: b[k] for k in ("date", "close")} for b in bars], **out})



@research_bp.route("/api/crash_windows")
def crash_windows():
    """Indicative crash windows for a date range (planetary-combination score; research only)."""
    from sbc.crash_windows import build

    try:
        start_d = datetime.date.fromisoformat(request.args.get("start") or "")
        end_d = datetime.date.fromisoformat(request.args.get("end") or "")
    except (TypeError, ValueError):
        return jsonify({"error": "invalid start/end date"}), 400
    if end_d < start_d:
        return jsonify({"error": "end before start"}), 400
    if (end_d - start_d).days > 730:
        return jsonify({"error": "range too large (max 2 years)"}), 400
    return jsonify(build(start_d, end_d))


@research_bp.route("/api/economic/indicators")
def economic_indicators():
    """Return economic indicators for a date range.
    
    Query params:
        series: Filter by series ID (optional, e.g., "FEDFUNDS")
        start: Start date YYYY-MM-DD (optional)
        end: End date YYYY-MM-DD (optional)
    """
    from sbc.economic_data import get_economic_data
    
    series = request.args.get("series")
    start = request.args.get("start")
    end = request.args.get("end")
    
    try:
        data = get_economic_data(series=series, start=start, end=end)
        return jsonify(data)
    except Exception as e:
        return internal_error()


@research_bp.route("/api/economic/refresh", methods=["POST"])
def economic_refresh():
    """Refresh economic data from FRED API.
    
    Query params:
        years: Number of years to fetch (default: 10)
    """
    from sbc.economic_data import refresh_fred_data
    
    try:
        years = int(request.args.get("years", 10))
        years = max(1, min(20, years))  # Limit to 1-20 years
    except ValueError:
        return jsonify({"error": "years must be an integer"}), 400
    
    try:
        results = refresh_fred_data(years=years)
        return jsonify(results)
    except Exception as e:
        return internal_error()


@research_bp.route("/api/sentiment/daily")
def sentiment_daily():
    """Return daily sentiment scores for a date range.
    
    Query params:
        source: Filter by source (vix, news, twitter) (optional)
        ticker: Filter by ticker (optional)
        start: Start date YYYY-MM-DD (optional)
        end: End date YYYY-MM-DD (optional)
    """
    from sbc.sentiment_data import get_sentiment_data
    
    source = request.args.get("source")
    ticker = request.args.get("ticker")
    start = request.args.get("start")
    end = request.args.get("end")
    
    try:
        data = get_sentiment_data(source=source, ticker=ticker, start=start, end=end)
        return jsonify(data)
    except Exception as e:
        return internal_error()


@research_bp.route("/api/sentiment/refresh", methods=["POST"])
def sentiment_refresh():
    """Refresh sentiment data from Twitter, news, and VIX.
    
    Query params:
        days: Number of days to fetch (default: 90)
        ticker: Ticker to search for in news (default: "NIFTY 50")
    """
    from sbc.sentiment_data import refresh_sentiment_data
    
    try:
        days = int(request.args.get("days", 90))
        days = max(1, min(365, days))  # Limit to 1-365 days
        ticker = request.args.get("ticker", "NIFTY 50")
    except ValueError:
        return jsonify({"error": "days must be an integer"}), 400
    
    try:
        results = refresh_sentiment_data(days=days, ticker=ticker)
        return jsonify(results)
    except Exception as e:
        return internal_error()
