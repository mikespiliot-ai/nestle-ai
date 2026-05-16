"""
Binance Testnet paper trading executor.
Sends real orders to testnet.binance.vision — 100% safe, fake money.
Testnet keys: https://testnet.binance.vision/
"""

import hashlib
import hmac
import logging
import time
import urllib.parse
from typing import Dict, List, Optional

import requests

logger = logging.getLogger(__name__)

TESTNET_BASE = "https://testnet.binance.vision/api/v3"
TESTNET_WS   = "wss://testnet.binance.vision/ws"


class BinanceTestnetClient:
    def __init__(self, api_key: str, secret: str):
        self.api_key = api_key
        self.secret  = secret
        self.session = requests.Session()
        self.session.headers.update({
            "X-MBX-APIKEY": api_key,
            "Content-Type": "application/x-www-form-urlencoded",
        })

    # ── Account ──────────────────────────────────────────────────────────────

    def get_account(self) -> Dict:
        return self._signed_get("/account")

    def get_balances(self) -> Dict[str, float]:
        data = self.get_account()
        return {
            b["asset"]: float(b["free"]) + float(b["locked"])
            for b in data.get("balances", [])
            if float(b["free"]) + float(b["locked"]) > 0
        }

    def get_open_orders(self, symbol: str = "") -> List[Dict]:
        params = {"symbol": symbol} if symbol else {}
        return self._signed_get("/openOrders", params)

    # ── Orders ───────────────────────────────────────────────────────────────

    def market_buy(self, symbol: str, quote_qty: float) -> Optional[Dict]:
        """Buy using USDT amount (quoteOrderQty)."""
        return self._signed_post("/order", {
            "symbol":        symbol,
            "side":          "BUY",
            "type":          "MARKET",
            "quoteOrderQty": f"{quote_qty:.2f}",
        })

    def market_sell(self, symbol: str, quantity: float) -> Optional[Dict]:
        """Sell exact quantity of base asset."""
        info = self._get_symbol_info(symbol)
        qty  = self._round_qty(quantity, info)
        if qty <= 0:
            logger.warning("[BinanceTestnet] Rounded qty=0 for %s — skipping", symbol)
            return None
        return self._signed_post("/order", {
            "symbol":   symbol,
            "side":     "SELL",
            "type":     "MARKET",
            "quantity": f"{qty}",
        })

    def cancel_all_orders(self, symbol: str) -> List[Dict]:
        return self._signed_delete(f"/openOrders", {"symbol": symbol})

    # ── Market data (public) ──────────────────────────────────────────────────

    def get_price(self, symbol: str) -> float:
        resp = self.session.get(f"{TESTNET_BASE}/ticker/price", params={"symbol": symbol}, timeout=10)
        if resp.status_code == 200:
            return float(resp.json()["price"])
        return 0.0

    def get_prices(self) -> Dict[str, float]:
        resp = self.session.get(f"{TESTNET_BASE}/ticker/price", timeout=10)
        if resp.status_code == 200:
            return {item["symbol"]: float(item["price"]) for item in resp.json()}
        return {}

    def get_exchange_info(self) -> Dict:
        resp = self.session.get(f"{TESTNET_BASE}/exchangeInfo", timeout=15)
        resp.raise_for_status()
        return resp.json()

    def ping(self) -> bool:
        try:
            resp = self.session.get(f"{TESTNET_BASE}/ping", timeout=5)
            return resp.status_code == 200
        except Exception:
            return False

    # ── Internals ─────────────────────────────────────────────────────────────

    def _signed_get(self, path: str, params: dict = None) -> Dict:
        params = params or {}
        params["timestamp"] = int(time.time() * 1000)
        params["signature"] = self._sign(params)
        resp = self.session.get(f"{TESTNET_BASE}{path}", params=params, timeout=15)
        self._raise_for_status(resp)
        return resp.json()

    def _signed_post(self, path: str, params: dict) -> Optional[Dict]:
        params["timestamp"] = int(time.time() * 1000)
        params["signature"] = self._sign(params)
        resp = self.session.post(f"{TESTNET_BASE}{path}", data=params, timeout=15)
        self._raise_for_status(resp)
        return resp.json()

    def _signed_delete(self, path: str, params: dict) -> List:
        params["timestamp"] = int(time.time() * 1000)
        params["signature"] = self._sign(params)
        resp = self.session.delete(f"{TESTNET_BASE}{path}", params=params, timeout=15)
        self._raise_for_status(resp)
        return resp.json()

    def _sign(self, params: dict) -> str:
        query = urllib.parse.urlencode(params)
        return hmac.new(self.secret.encode(), query.encode(), hashlib.sha256).hexdigest()

    def _raise_for_status(self, resp: requests.Response):
        if resp.status_code != 200:
            logger.error("[BinanceTestnet] %s %s — %s", resp.status_code, resp.url, resp.text[:200])
            resp.raise_for_status()

    _symbol_info_cache: Dict[str, Dict] = {}

    def _get_symbol_info(self, symbol: str) -> Dict:
        if symbol not in self._symbol_info_cache:
            info = self.get_exchange_info()
            for s in info.get("symbols", []):
                self._symbol_info_cache[s["symbol"]] = s
        return self._symbol_info_cache.get(symbol, {})

    @staticmethod
    def _round_qty(qty: float, symbol_info: Dict) -> float:
        """Round quantity to exchange step size."""
        for f in symbol_info.get("filters", []):
            if f["filterType"] == "LOT_SIZE":
                step = float(f["stepSize"])
                if step > 0:
                    precision = len(str(step).rstrip("0").split(".")[-1])
                    return round(int(qty / step) * step, precision)
        return round(qty, 6)
