"""
Virtual portfolio state management backed by SQLite.
Tracks holdings, cash, trade history, and daily NAV.
"""

import json
import logging
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional

from config import INITIAL_CAPITAL_USD

logger = logging.getLogger(__name__)


class Portfolio:
    def __init__(self, db_path: str = "paper_trading/portfolio.db"):
        import os
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.db_path = db_path
        self._init_db()

    # ── DB setup ─────────────────────────────────────────────────────────────

    def _init_db(self):
        with self._conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS holdings (
                    symbol TEXT PRIMARY KEY,
                    quantity REAL NOT NULL DEFAULT 0,
                    avg_entry_price REAL NOT NULL DEFAULT 0,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS cash (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    amount REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    side TEXT NOT NULL,
                    quantity REAL NOT NULL,
                    price REAL NOT NULL,
                    cost_usd REAL NOT NULL,
                    fee_usd REAL NOT NULL,
                    executed_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS nav_history (
                    date TEXT PRIMARY KEY,
                    nav REAL NOT NULL
                );
                INSERT OR IGNORE INTO cash (id, amount) VALUES (1, ?);
            """, (INITIAL_CAPITAL_USD,))

    def _conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    # ── Holdings ─────────────────────────────────────────────────────────────

    def get_holdings(self) -> Dict[str, Dict]:
        with self._conn() as conn:
            rows = conn.execute("SELECT symbol, quantity, avg_entry_price FROM holdings WHERE quantity > 0").fetchall()
        return {r[0]: {"quantity": r[1], "avg_entry_price": r[2]} for r in rows}

    def get_cash(self) -> float:
        with self._conn() as conn:
            row = conn.execute("SELECT amount FROM cash WHERE id = 1").fetchone()
        return float(row[0]) if row else INITIAL_CAPITAL_USD

    def update_holding(self, symbol: str, quantity_delta: float, price: float):
        now = datetime.utcnow().isoformat()
        with self._conn() as conn:
            row = conn.execute(
                "SELECT quantity, avg_entry_price FROM holdings WHERE symbol = ?", (symbol,)
            ).fetchone()
            if row:
                old_qty, old_avg = row
            else:
                old_qty, old_avg = 0.0, 0.0

            new_qty = old_qty + quantity_delta
            if new_qty <= 0:
                conn.execute("DELETE FROM holdings WHERE symbol = ?", (symbol,))
            else:
                if quantity_delta > 0:
                    new_avg = (old_qty * old_avg + quantity_delta * price) / new_qty
                else:
                    new_avg = old_avg
                conn.execute("""
                    INSERT OR REPLACE INTO holdings (symbol, quantity, avg_entry_price, updated_at)
                    VALUES (?, ?, ?, ?)
                """, (symbol, new_qty, new_avg, now))

    def update_cash(self, delta: float):
        with self._conn() as conn:
            conn.execute("UPDATE cash SET amount = amount + ? WHERE id = 1", (delta,))

    def record_trade(self, symbol: str, side: str, quantity: float, price: float, fee: float):
        cost = quantity * price
        with self._conn() as conn:
            conn.execute("""
                INSERT INTO trades (symbol, side, quantity, price, cost_usd, fee_usd, executed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (symbol, side, quantity, price, cost, fee, datetime.utcnow().isoformat()))

    # ── NAV ──────────────────────────────────────────────────────────────────

    def compute_nav(self, price_map: Dict[str, float]) -> float:
        holdings = self.get_holdings()
        portfolio_value = sum(
            h["quantity"] * price_map.get(sym, 0.0)
            for sym, h in holdings.items()
        )
        return self.get_cash() + portfolio_value

    def record_nav(self, nav: float):
        today = datetime.utcnow().strftime("%Y-%m-%d")
        with self._conn() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO nav_history (date, nav) VALUES (?, ?)",
                (today, nav),
            )

    def get_nav_history(self) -> List[Dict]:
        with self._conn() as conn:
            rows = conn.execute("SELECT date, nav FROM nav_history ORDER BY date").fetchall()
        return [{"date": r[0], "nav": r[1]} for r in rows]

    def get_trade_history(self) -> List[Dict]:
        with self._conn() as conn:
            rows = conn.execute("""
                SELECT symbol, side, quantity, price, cost_usd, fee_usd, executed_at
                FROM trades ORDER BY executed_at DESC LIMIT 200
            """).fetchall()
        keys = ["symbol", "side", "quantity", "price", "cost_usd", "fee_usd", "executed_at"]
        return [dict(zip(keys, r)) for r in rows]

    # ── Weights ──────────────────────────────────────────────────────────────

    def get_current_weights(self, price_map: Dict[str, float]) -> Dict[str, float]:
        nav = self.compute_nav(price_map)
        if nav <= 0:
            return {}
        holdings = self.get_holdings()
        return {
            sym: (h["quantity"] * price_map.get(sym, 0.0)) / nav
            for sym, h in holdings.items()
        }

    # ── State snapshot ────────────────────────────────────────────────────────

    def get_state(self) -> Dict:
        nav_hist = self.get_nav_history()
        nav = nav_hist[-1]["nav"] if nav_hist else INITIAL_CAPITAL_USD
        return {
            "nav": nav,
            "cash": self.get_cash(),
            "holdings": self.get_holdings(),
            "nav_history": nav_hist[-30:],
            "mode": "NORMAL",
        }

    def set_mode(self, mode: str):
        """Track whether portfolio is in DEFENSIVE or NORMAL mode."""
        with self._conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT);
                INSERT OR REPLACE INTO metadata (key, value) VALUES ('mode', ?);
            """, (mode,))
