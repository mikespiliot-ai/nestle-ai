"""
Live price and market data fetching via CoinGecko and Binance.
"""

import logging
import requests
import time
from typing import Dict, List, Optional

from config import (
    COINGECKO_BASE_URL,
    BINANCE_BASE_URL,
    COINGECKO_CALLS_PER_MIN,
)

logger = logging.getLogger(__name__)
_RATE_DELAY = 60.0 / COINGECKO_CALLS_PER_MIN


def get_current_prices(coin_ids: List[str], api_key: str = "") -> Dict[str, float]:
    """Return {coin_id: price_usd} for a list of CoinGecko IDs."""
    headers = {}
    if api_key:
        headers["x-cg-demo-api-key"] = api_key

    prices = {}
    chunk_size = 50
    for i in range(0, len(coin_ids), chunk_size):
        chunk = coin_ids[i : i + chunk_size]
        url = f"{COINGECKO_BASE_URL}/simple/price"
        params = {"ids": ",".join(chunk), "vs_currencies": "usd"}
        try:
            resp = requests.get(url, params=params, headers=headers, timeout=20)
            resp.raise_for_status()
            data = resp.json()
            for cid, vals in data.items():
                prices[cid] = vals.get("usd", 0.0)
        except requests.RequestException as e:
            logger.error("Live price fetch failed: %s", e)
        time.sleep(_RATE_DELAY)

    return prices


def get_binance_ohlcv(symbol: str, interval: str = "1d", limit: int = 30) -> Optional[List]:
    """
    Fetch OHLCV candles from Binance.
    symbol: e.g. 'BTCUSDT'
    Returns list of [open_time, open, high, low, close, volume, ...]
    """
    url = f"{BINANCE_BASE_URL}/klines"
    params = {"symbol": symbol, "interval": interval, "limit": limit}
    try:
        resp = requests.get(url, params=params, timeout=20)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        logger.warning("Binance OHLCV failed for %s: %s", symbol, e)
        return None


def get_fear_greed_index() -> Dict:
    """Fetch Alternative.me Fear & Greed Index (free, no key)."""
    try:
        resp = requests.get("https://api.alternative.me/fng/?limit=1", timeout=10)
        resp.raise_for_status()
        data = resp.json()
        entry = data["data"][0]
        return {
            "value": int(entry["value"]),
            "classification": entry["value_classification"],
        }
    except Exception as e:
        logger.warning("Fear & Greed fetch failed: %s", e)
        return {"value": 50, "classification": "Neutral"}


def get_global_crypto_data(api_key: str = "") -> Dict:
    """
    Fetch global crypto market data: total market cap, BTC dominance.
    """
    headers = {}
    if api_key:
        headers["x-cg-demo-api-key"] = api_key
    try:
        url = f"{COINGECKO_BASE_URL}/global"
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json().get("data", {})
        return {
            "total_market_cap_usd": data.get("total_market_cap", {}).get("usd", 0),
            "total_volume_usd": data.get("total_volume", {}).get("usd", 0),
            "btc_dominance": data.get("market_cap_percentage", {}).get("btc", 0),
            "eth_dominance": data.get("market_cap_percentage", {}).get("eth", 0),
            "market_cap_change_24h": data.get("market_cap_change_percentage_24h_usd", 0),
        }
    except Exception as e:
        logger.warning("Global crypto data fetch failed: %s", e)
        return {}
