"""
Historical OHLCV data fetching and caching.
Fetches monthly returns for the rolling 60-month window.
Includes dead/delisted coins to prevent survivorship bias.
"""

import os
import json
import time
import logging
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import requests
import pandas as pd
import numpy as np

from config import (
    COINGECKO_BASE_URL,
    ROLLING_WINDOW_MONTHS,
    MIN_HISTORY_MONTHS,
    COINGECKO_CALLS_PER_MIN,
)

logger = logging.getLogger(__name__)

CACHE_DIR = "data/cache"
_RATE_DELAY = 60.0 / COINGECKO_CALLS_PER_MIN


def _cache_path(coin_id: str) -> str:
    os.makedirs(CACHE_DIR, exist_ok=True)
    h = hashlib.md5(coin_id.encode()).hexdigest()[:8]
    return os.path.join(CACHE_DIR, f"{coin_id}_{h}.json")


def _load_cache(coin_id: str) -> Optional[Dict]:
    path = _cache_path(coin_id)
    if not os.path.exists(path):
        return None
    with open(path) as f:
        cached = json.load(f)
    # Invalidate if older than 24 hours
    saved_at = datetime.fromisoformat(cached.get("saved_at", "2000-01-01"))
    if datetime.utcnow() - saved_at > timedelta(hours=24):
        return None
    return cached


def _save_cache(coin_id: str, data: Dict) -> None:
    data["saved_at"] = datetime.utcnow().isoformat()
    with open(_cache_path(coin_id), "w") as f:
        json.dump(data, f)


def fetch_monthly_prices(coin_id: str, api_key: str = "", months: int = ROLLING_WINDOW_MONTHS) -> Optional[pd.Series]:
    """
    Fetch monthly closing prices for a coin.
    Returns a pd.Series indexed by month-end date, or None if insufficient data.
    """
    cached = _load_cache(coin_id)
    if cached and "prices" in cached:
        prices_raw = cached["prices"]
    else:
        headers = {}
        if api_key:
            headers["x-cg-demo-api-key"] = api_key

        days = months * 31 + 10
        url = f"{COINGECKO_BASE_URL}/coins/{coin_id}/market_chart"
        params = {"vs_currency": "usd", "days": days, "interval": "daily"}

        try:
            resp = requests.get(url, params=params, headers=headers, timeout=60)
            resp.raise_for_status()
            raw = resp.json()
        except requests.RequestException as e:
            logger.warning("Failed to fetch history for %s: %s", coin_id, e)
            return None

        prices_raw = raw.get("prices", [])
        _save_cache(coin_id, {"prices": prices_raw})
        time.sleep(_RATE_DELAY)

    if not prices_raw:
        return None

    df = pd.DataFrame(prices_raw, columns=["ts_ms", "price"])
    df["date"] = pd.to_datetime(df["ts_ms"], unit="ms")
    df.set_index("date", inplace=True)
    df.drop(columns=["ts_ms"], inplace=True)

    # Resample to month-end
    monthly = df["price"].resample("ME").last().dropna()

    if len(monthly) < MIN_HISTORY_MONTHS:
        return None

    return monthly.tail(months + 1)


def compute_monthly_returns(prices: pd.Series) -> pd.Series:
    return prices.pct_change().dropna()


def build_returns_matrix(
    coin_ids: List[str],
    api_key: str = "",
    months: int = ROLLING_WINDOW_MONTHS,
) -> pd.DataFrame:
    """
    Build a T×p DataFrame of monthly returns for all coins in the universe.
    Drops coins with insufficient history.
    """
    returns: Dict[str, pd.Series] = {}

    for coin_id in coin_ids:
        prices = fetch_monthly_prices(coin_id, api_key=api_key, months=months)
        if prices is not None:
            ret = compute_monthly_returns(prices)
            returns[coin_id] = ret
        else:
            logger.debug("Skipping %s — insufficient history", coin_id)

    if not returns:
        return pd.DataFrame()

    df = pd.DataFrame(returns)
    # Keep only rows where at least 50% of assets have data
    df = df.dropna(thresh=max(1, len(df.columns) // 2))
    return df
