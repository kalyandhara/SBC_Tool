"""
Render daily intraday financial astrology report.
"""
import sqlite3
from pathlib import Path
from datetime import datetime

DB_PATH = Path(__file__).resolve().parent / "navamsa.db"

def load_day(date_str):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT * FROM intraday_triggers WHERE DATE(timestamp) = ?", (date_str,))
    cols = [d[0] for d in cur.description]
    rows = [dict(zip(cols, r)) for r in cur.fetchall()]
    conn.close()
    return rows

def format_daily_report(date_str, ayanamsha="KP"):
    rows = load_day(date_str)
    if not rows:
        return f"No data for {date_str}"
    header = f"""NIFTY 50 — INTRADAY FINANCIAL ASTROLOGY VIEW
NSE, Exchange Plaza, Bandra Kurla Complex, Mumbai  |  19.0656°N 72.8646°E  |  IST (UTC+5:30)
Ayanamsa: {ayanamsha}   Houses: Placidus (KP)   Node: TRUE
Generated {datetime.now().strftime('%d-%b-%Y %H:%M')} IST
"""
    # Simple table
    lines = ["Time,Score,Market View,Conv,Nakshatra,Sub-lord,Score,Grade"]
    for r in rows[::15]:  # sample every 15 rows
        time = r['timestamp'][11:16]
        score = r['score']
        grade = r['grade']
        nak = r['nakshatra']
        sub = r['sublord']
        lines.append(f"{time},{score},{grade},{grade},{nak},{sub},{score},{grade}")
    body = "\n".join(lines)
    return header + "\n" + body
