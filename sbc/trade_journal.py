"""Trade journal for AUGMONT-style breakout logs (B-48).

Stores entry, partial exits, final exit with R-multiple.

Data stored in data/trade_journal.db table trades:
  id, symbol, entry_date, entry_price, qty, direction, stop_price, risk_per_share,
  notes, created_at
  exits table: trade_id, exit_date, exit_price, qty, type (partial/final)

API: /api/engine/trade_journal
"""

from __future__ import annotations

import datetime as dt
import sqlite3
from pathlib import Path
from typing import List, Dict

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "trade_journal.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

def _conn():
    conn = sqlite3.connect(str(DB_PATH))
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            entry_date TEXT NOT NULL,
            entry_price REAL NOT NULL,
            qty REAL NOT NULL,
            direction TEXT NOT NULL CHECK(direction IN ('long','short')),
            stop_price REAL,
            risk_per_share REAL,
            notes TEXT,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS exits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trade_id INTEGER NOT NULL,
            exit_date TEXT NOT NULL,
            exit_price REAL NOT NULL,
            qty REAL NOT NULL,
            type TEXT NOT NULL CHECK(type IN ('partial','final')),
            FOREIGN KEY(trade_id) REFERENCES trades(id)
        );
    """)
    return conn

def create_trade(symbol: str, entry_date: str, entry_price: float, qty: float,
                 direction: str, stop_price: float | None = None,
                 risk_per_share: float | None = None, notes: str = "") -> int:
    with _conn() as c:
        c.execute(
            "INSERT INTO trades(symbol,entry_date,entry_price,qty,direction,stop_price,risk_per_share,notes,created_at) VALUES (?,?,?,?,?,?,?,?,?)",
            (symbol, entry_date, entry_price, qty, direction, stop_price, risk_per_share, notes, dt.datetime.utcnow().isoformat())
        )
        return c.lastrowid

def add_exit(trade_id: int, exit_date: str, exit_price: float, qty: float, type_: str = "partial"):
    with _conn() as c:
        c.execute("INSERT INTO exits(trade_id,exit_date,exit_price,qty,type) VALUES (?,?,?,?,?)",
                  (trade_id, exit_date, exit_price, qty, type_))

def get_trade(trade_id: int) -> Dict:
    with _conn() as c:
        row = c.execute("SELECT * FROM trades WHERE id=?", (trade_id,)).fetchone()
        if not row:
            return {}
        cols = [d[0] for d in c.description]
        trade = dict(zip(cols, row))
        exits = c.execute("SELECT * FROM exits WHERE trade_id=? ORDER BY exit_date", (trade_id,)).fetchall()
        ecols = [d[0] for d in c.description]
        trade["exits"] = [dict(zip(ecols, e)) for e in exits]
        # compute R-multiple if risk known
        if trade.get("risk_per_share"):
            entry = trade["entry_price"]
            direction = 1 if trade["direction"] == "long" else -1
            total_r = 0.0
            for ex in trade["exits"]:
                pnl_per_share = direction * (ex["exit_price"] - entry)
                r = pnl_per_share / trade["risk_per_share"]
                total_r += r * ex["qty"] / trade["qty"]
            trade["r_multiple"] = total_r
        return trade

def list_trades(symbol: str | None = None, limit: int = 100) -> List[Dict]:
    with _conn() as c:
        if symbol:
            rows = c.execute("SELECT id FROM trades WHERE symbol=? ORDER BY entry_date DESC LIMIT ?", (symbol, limit)).fetchall()
        else:
            rows = c.execute("SELECT id FROM trades ORDER BY entry_date DESC LIMIT ?", (limit,)).fetchall()
        return [get_trade(r[0]) for r in rows]
