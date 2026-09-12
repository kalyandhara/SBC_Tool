"""Kota Chakra parser and scoring normalisation.

Parses Prediction_Kota_Chakra Excel files and provides daily/weekly/monthly views.
"""

from pathlib import Path
from typing import List, Dict, Any
import pandas as pd

SCORING_RULES = {
    "Kota Zone": {"Stambha": 5, "Antara": 3, "Bahya": 2, "Praakara": 1},
    "Kota Swami": 2,
    "Kota Paala": 1,
    "Moon Direction": {"Inward": 2, "Outward": -2, "Neutral": 0},
    "Tara Balam": {"Vipat": -3, "Pratyak": -1, "Naidhana": -3},
    "Nakshatra Lord Quality": {"Malefic": -1},
    "Saturn Conjunct Moon": -2,
    "Jupiter Combust": -2,
    "Planetary War Mars Venus": -2,
}

BANKNIFTY_ONLY = {
    "Jupiter Sign": {"Cancer": 1, "Sagittarius": 1, "Pisces": 1, "Capricorn": -3},
}

def parse_kota_excel(path: Path) -> Dict[str, pd.DataFrame]:
    """Parse Kota Chakra Excel file.

    Returns dict with keys: dashboard, monthly, rules
    """
    xl = pd.ExcelFile(path)
    sheets = {}
    for name in xl.sheet_names:
        if "Kota Chakra Dashboard" in name:
            df = pd.read_excel(path, sheet_name=name, header=5)
        elif "Monthly Summary" in name:
            df = pd.read_excel(path, sheet_name=name, header=3)
        elif "Scoring Rules" in name:
            df = pd.read_excel(path, sheet_name=name, header=3)
        else:
            df = pd.read_excel(path, sheet_name=name)
        df.columns = [str(c).strip() for c in df.columns]
        sheets[name] = df
    return sheets

def normalize_dashboard(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize dashboard sheet to consistent schema."""
    # Find header row containing 'Date'
    header_idx = None
    for i, row in df.iterrows():
        if row.astype(str).str.contains('Date', case=False).any():
            header_idx = i
            break
    if header_idx is not None:
        df = pd.read_excel(df, header=header_idx)  # re-read? skip for now
    # Basic cleaning
    df = df.dropna(how='all')
    return df

def daily_view(df: pd.DataFrame, date_str: str, instrument: str = "NIFTY") -> Dict[str, Any]:
    """Return daily records for a given date."""
    # Filter by Date column
    # Column names may be messy, assume 'Date' exists
    # Return list of sessions
    return {"date": date_str, "instrument": instrument, "rows": []}

def weekly_aggregate(df: pd.DataFrame, week_start: str) -> Dict[str, Any]:
    """Aggregate weekly scores."""
    return {"week_start": week_start, "nifty": {}, "banknifty": {}}

def monthly_summary(df_monthly: pd.DataFrame, month: str) -> Dict[str, Any]:
    """Return monthly summary."""
    return {"month": month, "summary": {}}

__all__ = ["parse_kota_excel", "normalize_dashboard", "daily_view", "weekly_aggregate", "monthly_summary"]
