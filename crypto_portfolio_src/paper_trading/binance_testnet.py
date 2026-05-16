"""Binance Testnet REST client with HMAC-SHA256 signing."""

import hashlib
import hmac
import logging
import time
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

import requests

from config import BINANCE_TESTNET_BASE

logger = logging.getLogger(__name__)

TESTNET_BASE = BINANCE_TESTNET_BASE


class BinanceTestnetClient:
    """Minimal REST client for the Binance SPOT Testnet."""

    def __init__(self, api_key: str, secret: str):
        self._api_key = api_key
        self._secret = secret
        self._session = requests.Session()
        self._session.headers.update({"X-MBX-APIKEY": api_key})

    # ── Signing ───────────────────────────────────────────────────────────────

    def _sign(self, params: Dict[str, Any]) -> str:
        query = urlencode(params)
        return hmac.new(
            self._secret.encode("utf-8"),
            query.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    def _signed_params(self, params: Optional[Dict] = None) -> Dict:
        p = params.copy() if params else {}
        p["timestamp"] = int(time.time() * 1000)
        p["signature"] = self._sign(p)
        return p

    # ── Public endpoints ──────────────────────────────────────────────────────

    def ping(self) -> bool:
        try:
            r = self._session.get(f"{TESTNET_BASE}/ping", timeout=10)
            return r.status_code == 200
        except Exception:
            return False

    def get_price(self, symbol: str) -> Optional[float]:
        try:
            r = self._session.get(
                f"{TESTNET_BASE}/ticker/price", params={"symbol": symbol}, timeout=10
            )
            r.raise_for_status()
            return float(r.json()["price"])
        except Exception as exc:
            logger.error("get_price(%s) error: %s", symbol, exc)
            return None

    def get_prices(self) -> Dict[str, float]:
        try:
            r = self._session.get(f"{TESTNET_BASE}/ticker/price", timeout=10)
            r.raise_for_status()
            return {item["symbol"]: float(item["price"]) for item in r.json()}
        except Exception as exc:
            logger.error("get_prices error: %s", exc)
            return {}

    def get_exchange_info(self) -> Dict[str, Any]:
        try:
            r = self._session.get(f"{TESTNET_BASE}/exchangeInfo", timeout=20)
            r.raise_for_status()
            return r.json()
        except Exception as exc:
            logger.error("get_exchange_info error: %s", exc)
            return {}

    # ── Account endpoints ─────────────────────────────────────────────────────

    def get_account(self) -> Dict[str, Any]:
        try:
            p = self._signed_params()
            r = self._session.get(f"{TESTNET_BASE}/account", params=p, timeout=15)
            r.raise_for_status()
            return r.json()
        except Exception as exc:
            logger.error("get_account error: %s", exc)
            return {}

    def get_balances(self) -> Dict[str, float]:
        account = self.get_account()
        balances: Dict[str, float] = {}
        for b in account.get("balances", []):
            free = float(b.get("free", 0))
            if free > 0:
                balances[b["asset"]] = free
        return balances

    def get_open_orders(self, symbol: Optional[str] = None) -> List[Dict]:
        try:
            params: Dict[str, Any] = {}
            if symbol:
                params["symbol"] = symbol
            p = self._signed_params(params)
            r = self._session.get(f"{TESTNET_BASE}/openOrders", params=p, timeout=15)
            r.raise_for_status()
            return r.json()
        except Exception as exc:
            logger.error("get_open_orders error: %s", exc)
            return []

    # ── Order endpoints ───────────────────────────────────────────────────────

    def market_buy(self, symbol: str, quote_qty: float) -> Dict[str, Any]:
        """Market buy using quoteOrderQty (spend *quote_qty* USDT)."""
        params = {
            "symbol": symbol,
            "side": "BUY",
            "type": "MARKET",
            "quoteOrderQty": round(quote_qty, 2),
        }
        return self._place_order(params)

    def market_sell(self, symbol: str, quantity: float) -> Dict[str, Any]:
        """Market sell *quantity* units of the base asset."""
        qty_rounded = self._round_qty(symbol, quantity)
        params = {
            "symbol": symbol,
            "side": "SELL",
            "type": "MARKET",
            "quantity": qty_rounded,
        }
        return self._place_order(params)

    def _place_order(self, params: Dict[str, Any]) -> Dict[str, Any]:
        try:
            p = self._signed_params(params)
            r = self._session.post(f"{TESTNET_BASE}/order", params=p, timeout=20)
            r.raise_for_status()
            return r.json()
        except Exception as exc:
            logger.error("Order error (%s): %s", params.get("symbol"), exc)
            return {}

    # ── LOT_SIZE rounding ─────────────────────────────────────────────────────

    _lot_sizes: Dict[str, float] = {}

    def _round_qty(self, symbol: str, qty: float) -> float:
        if symbol not in self._lot_sizes:
            info = self.get_exchange_info()
            for sym in info.get("symbols", []):
                if sym["symbol"] == symbol:
                    for f in sym.get("filters", []):
                        if f["filterType"] == "LOT_SIZE":
                            self._lot_sizes[symbol] = float(f["stepSize"])
                            break
                    break
        step = self._lot_sizes.get(symbol, 1e-8)
        if step <= 0:
            return qty
        import math
        precision = max(0, -int(math.floor(math.log10(step))))
        return round(math.floor(qty / step) * step, precision)
