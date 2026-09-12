"""
Simple SQLite writer for pipeline outputs.
"""
import sqlite3
from pathlib import Path

DB_PATH = Path("D:/SBC_Tool - Copy/sbc/navamsa_pipeline/navamsa.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS intraday_triggers (
        timestamp TEXT,
        ayanamsa_offset REAL,
        moon_lon REAL,
        lagna_lon REAL,
        navamsa_sign TEXT,
        navamsa_index INTEGER,
        vargottama INTEGER,
        tithi TEXT,
        nakshatra TEXT,
        nakshatra_pada INTEGER,
        yoga TEXT,
        karana TEXT,
        hora_lord TEXT,
        house_set TEXT,
        sublord TEXT,
        sublord_change INTEGER,
        regime_shift INTEGER,
        pure_set_alarm INTEGER,
        confirmation_points INTEGER,
        score REAL,
        grade TEXT
    )
    """)
    conn.commit()
    conn.close()

def save_rows(rows):
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    for r in rows:
        cur.execute("""
        INSERT INTO intraday_triggers VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?, ?,?)
        """, (
            r.get('timestamp'),
            r.get('ayanamsa_offset'),
            r.get('moon_lon'),
            r.get('lagna_lon'),
            r.get('navamsa_sign'),
            r.get('navamsa_index'),
            int(r.get('vargottama')),
            r.get('tithi'),
            r.get('nakshatra'),
            r.get('nakshatra_pada'),
            r.get('yoga'),
            r.get('karana'),
            r.get('hora_lord'),
            r.get('house_set'),
            r.get('sublord'),
            int(r.get('sublord_change', False)),
            int(r.get('regime_shift', False)),
            int(r.get('pure_set_alarm', False)),
            int(r.get('confirmation_points', 0)),
            r.get('score'),
            r.get('grade')
        ))
    conn.commit()
    conn.close()
