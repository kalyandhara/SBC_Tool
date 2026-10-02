"""
Validation harness against historical OHLC.
"""

import pandas as pd


def load_ohlc(path):
    df = pd.read_csv(path, parse_dates=["Date"])
    return df

def validate(triggers_path, ohlc_path):
    triggers = pd.read_csv(triggers_path, parse_dates=["timestamp"])
    ohlc = load_ohlc(ohlc_path)
    # Simple join on date
    triggers["date"] = triggers["timestamp"].dt.date
    ohlc["date"] = pd.to_datetime(ohlc["Date"]).dt.date
    merged = triggers.merge(ohlc, on="date", how="left")
    # Compute basic metrics placeholder
    hits = merged[merged["signal_grade"]=="Tier1"].shape[0]
    total = merged.shape[0]
    precision = hits/total if total else 0
    return {
        "total_signals": int(total),
        "tier1_count": int(hits),
        "precision_placeholder": round(precision,4)
    }
