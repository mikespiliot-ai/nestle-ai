"""SQLite-backed paper trading portfolio."""

import logging
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from config import INITIAL_CAPITAL_USD

logger = logging.getLogger(__name__)

_DDL = """
CREATE TABLE IF NOT EXISTS holdings (
    coin_id     TEXT PRIMARY KEY,
    quantity    REAL NOT NULL DEFAULT 0.0,
    avg_cost    REAL NOT NULL DEFAULT 0.0,
    updated_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS cash (
    id      INTEGER PRIMARY KEY CHECK (id = 1),
    balance REAL NOT NULL DEFAULT 0.0
);

CREATE TABLE IF NOT EXISTS trades (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp   TEXT NOT NULL,
    coin_id     TEXT NOT NULL,
    side        TEXT NOT NULL,
    quantity    REAL NOT NULL,
    price       REAL NOT NULL,
    fee         REAL NOT NULL DEFAULT 0.0,
    nav_after   REAL
);

CREATE TABLE IF NOT EXISTS nav_history (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp   TEXT NOT NULL,
    nav         REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS metadata (
    key     TEXT PRIMARY KEY,
    value   TEXT NOT NULL
);
"""


class Portfolio:
    """Persistent paper trading portfolio backed by SQLite."""

    def __init__(self, db_path: str = "paper_trading/portfolio.db"):
        self._db_path = db_path
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        conn = self._connect()
        try:
            conn.executescript(_DDL)
            conn.execute(
                "INSERT OR IGNORE INTO cash (id, balance) VALUES (1, ?)",
                (INITIAL_CAPITAL_USD,),
            )
            conn.commit()
        finally:
            conn.close()

    # ── Holdings ──────────────────────────────────────────────────────────────

    def get_holdings(self) -> Dict[str, Dict[str, float]]:
        conn = self._connect()
        try:
            rows = conn.execute(
                "SELECT coin_id, quantity, avg_cost FROM holdings WHERE quantity > 0"
            ).fetchall()
            return {r["coin_id"]: {"quantity": r["quantity"], "avg_cost": r["avg_cost"]} for r in rows}
        finally:
            conn.close()

    def update_holding(self, coin_id: str, quantity: float, avg_cost: float) -> None:
        now = datetime.now(timezone.utc).isoformat()
        conn = self._connect()
        try:
            conn.execute(
                """INSERT INTO holdings (coin_id, quantity, avg_cost, updated_at)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(coin_id) DO UPDATE SET
                   quantity=excluded.quantity,
                   avg_cost=excluded.avg_cost,
                   updated_at=excluded.updated_at""",
                (coin_id, quantity, avg_cost, now),
            )
            conn.commit()
        finally:
            conn.close()

    # ── Cash ──────────────────────────────────────────────────────────────────

    def get_cash(self) -> float:
        conn = self._connect()
        try:
            row = conn.execute("SELECT balance FROM cash WHERE id = 1").fetchone()
            return row["balance"] if row else 0.0
        finally:
            conn.close()

    def update_cash(self, new_balance: float) -> None:
        conn = self._connect()
        try:
            conn.execute("UPDATE cash SET balance = ? WHERE id = 1", (new_balance,))
            conn.commit()
        finally:
            conn.close()

    # ── Trades ────────────────────────────────────────────────────────────────

    def record_trade(
        self,
        coin_id: str,
        side: str,
        quantity: float,
        price: float,
        fee: float = 0.0,
        nav_after: Optional[float] = None,
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        conn = self._connect()
        try:
            conn.execute(
                """INSERT INTO trades (timestamp, coin_id, side, quantity, price, fee, nav_after)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (now, coin_id, side, quantity, price, fee, nav_after),
            )
            conn.commit()
        finally:
            conn.close()

    def get_trade_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        conn = self._connect()
        try:
            rows = conn.execute(
                "SELECT * FROM trades ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    # ── NAV ───────────────────────────────────────────────────────────────────

    def compute_nav(self, price_map: Dict[str, float]) -> float:
        holdings = self.get_holdings()
        cash = self.get_cash()
        asset_value = sum(
            h["quantity"] * price_map.get(cid, 0.0)
            for cid, h in holdings.items()
        )
        return cash + asset_value

    def record_nav(self, nav: float) -> None:
        now = datetime.now(timezone.utc).isoformat()
        conn = self._connect()
        try:
            conn.execute(
                "INSERT INTO nav_history (timestamp, nav) VALUES (?, ?)", (now, nav)
            )
            conn.commit()
        finally:
            conn.close()

    def get_nav_history(self, limit: int = 500) -> List[Dict[str, Any]]:
        conn = self._connect()
        try:
            rows = conn.execute(
                "SELECT timestamp, nav FROM nav_history ORDER BY id ASC LIMIT ?", (limit,)
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    # ── Weights ───────────────────────────────────────────────────────────────

    def get_current_weights(self, price_map: Dict[str, float]) -> Dict[str, float]:
        nav = self.compute_nav(price_map)
        if nav <= 0:
            return {}
        holdings = self.get_holdings()
        weights: Dict[str, float] = {}
        for cid, h in holdings.items():
            val = h["quantity"] * price_map.get(cid, 0.0)
            weights[cid] = val / nav
        return weights

    # ── State & mode ─────────────────────────────────────────────────────────

    def get_state(self) -> Dict[str, Any]:
        price_map: Dict[str, float] = {}  # caller should inject prices
        return {
            "cash":     self.get_cash(),
            "holdings": self.get_holdings(),
            "mode":     self._get_metadata("mode", "NORMAL"),
        }

    def set_mode(self, mode: str) -> None:
        self._set_metadata("mode", mode)

    def _get_metadata(self, key: str, default: str = "") -> str:
        conn = self._connect()
        try:
            row = conn.execute("SELECT value FROM metadata WHERE key = ?", (key,)).fetchone()
            return row["value"] if row else default
        finally:
            conn.close()

    def _set_metadata(self, key: str, value: str) -> None:
        conn = self._connect()
        try:
            conn.execute(
                "INSERT INTO metadata (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (key, value),
            )
            conn.commit()
        finally:
            conn.close()
