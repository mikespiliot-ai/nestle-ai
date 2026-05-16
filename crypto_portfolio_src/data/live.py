"""Live market data from CoinGecko, Binance, and alternative.me."""

import logging
from typing import Any, Dict, List, Optional

import requests

from config import (
    BINANCE_BASE_URL,
    COINGECKO_BASE_URL,
    FEAR_GREED_URL,
)

logger = logging.getLogger(__name__)


def get_current_prices(
    coin_ids: List[str],
    api_key: Optional[str] = None,
) -> Dict[str, float]:
    """Return {coin_id: usd_price} for all requested ids."""
    headers = {}
    if api_key:
        headers["x-cg-pro-api-key"] = api_key

    chunk_size = 50
    prices: Dict[str, float] = {}

    for i in range(0, len(coin_ids), chunk_size):
        chunk = coin_ids[i : i + chunk_size]
        params = {
            "ids": ",".join(chunk),
            "vs_currencies": "usd",
        }
        try:
            resp = requests.get(
                f"{COINGECKO_BASE_URL}/simple/price",
                params=params,
                headers=headers,
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            for cid, vals in data.items():
                prices[cid] = vals.get("usd", 0.0)
        except Exception as exc:
            logger.error("get_current_prices error: %s", exc)

    return prices


def get_binance_ohlcv(
    symbol: str,
    interval: str = "1d",
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """Fetch OHLCV klines from Binance."""
    url = f"{BINANCE_BASE_URL}/klines"
    params = {"symbol": symbol, "interval": interval, "limit": limit}
    try:
        resp = requests.get(url, params=params, timeout=20)
        resp.raise_for_status()
        raw = resp.json()
        candles = []
        for k in raw:
            candles.append(
                {
                    "open_time":  k[0],
                    "open":       float(k[1]),
                    "high":       float(k[2]),
                    "low":        float(k[3]),
                    "close":      float(k[4]),
                    "volume":     float(k[5]),
                    "close_time": k[6],
                }
            )
        return candles
    except Exception as exc:
        logger.error("get_binance_ohlcv error for %s: %s", symbol, exc)
        return []


def get_fear_greed_index() -> Dict[str, Any]:
    """Return the latest Fear & Greed Index data from alternative.me."""
    try:
        resp = requests.get(FEAR_GREED_URL, params={"limit": 1}, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        entry = data.get("data", [{}])[0]
        return {
            "value":             int(entry.get("value", 50)),
            "value_classification": entry.get("value_classification", "Neutral"),
            "timestamp":         entry.get("timestamp"),
        }
    except Exception as exc:
        logger.error("get_fear_greed_index error: %s", exc)
        return {"value": 50, "value_classification": "Neutral", "timestamp": None}


def get_global_crypto_data(api_key: Optional[str] = None) -> Dict[str, Any]:
    """Return global crypto market data from CoinGecko /global."""
    headers = {}
    if api_key:
        headers["x-cg-pro-api-key"] = api_key

    try:
        resp = requests.get(
            f"{COINGECKO_BASE_URL}/global",
            headers=headers,
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json().get("data", {})
        return {
            "total_market_cap_usd":        data.get("total_market_cap", {}).get("usd", 0),
            "total_volume_usd":            data.get("total_volume", {}).get("usd", 0),
            "btc_dominance":               data.get("market_cap_percentage", {}).get("btc", 0),
            "eth_dominance":               data.get("market_cap_percentage", {}).get("eth", 0),
            "market_cap_change_24h_pct":   data.get("market_cap_change_percentage_24h_usd", 0),
            "active_cryptocurrencies":     data.get("active_cryptocurrencies", 0),
        }
    except Exception as exc:
        logger.error("get_global_crypto_data error: %s", exc)
        return {}
