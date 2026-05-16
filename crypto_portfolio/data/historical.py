"""Historical price data fetching with local disk cache."""

import json
import logging
import os
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

import pandas as pd
import requests

from config import COINGECKO_BASE_URL, ROLLING_WINDOW_MONTHS

logger = logging.getLogger(__name__)

CACHE_DIR = "data/cache"
CACHE_TTL_SECONDS = 86_400  # 24 h


def _cache_path(coin_id: str, months: int) -> str:
    os.makedirs(CACHE_DIR, exist_ok=True)
    return os.path.join(CACHE_DIR, f"{coin_id}_{months}m.json")


def _cache_valid(path: str) -> bool:
    if not os.path.exists(path):
        return False
    mtime = datetime.fromtimestamp(os.path.getmtime(path), tz=timezone.utc)
    return (datetime.now(timezone.utc) - mtime).total_seconds() < CACHE_TTL_SECONDS


def fetch_monthly_prices(
    coin_id: str,
    api_key: Optional[str] = None,
    months: int = ROLLING_WINDOW_MONTHS,
) -> pd.Series:
    """Fetch monthly end-of-month prices for *coin_id*.

    Returns a ``pd.Series`` indexed by month-end date (UTC, period M).
    """
    cache = _cache_path(coin_id, months)
    if _cache_valid(cache):
        with open(cache) as fh:
            raw = json.load(fh)
        prices = raw["prices"]
    else:
        headers = {}
        if api_key:
            headers["x-cg-pro-api-key"] = api_key

        days = months * 31
        params = {"vs_currency": "usd", "days": days, "interval": "daily"}
        url = f"{COINGECKO_BASE_URL}/coins/{coin_id}/market_chart"
        try:
            resp = requests.get(url, params=params, headers=headers, timeout=60)
            resp.raise_for_status()
            prices = resp.json().get("prices", [])
        except Exception as exc:
            logger.error("fetch_monthly_prices error for %s: %s", coin_id, exc)
            return pd.Series(dtype=float, name=coin_id)

        with open(cache, "w") as fh:
            json.dump({"prices": prices, "fetched_at": datetime.now(timezone.utc).isoformat()}, fh)

        time.sleep(1.2)  # respect rate limit

    if not prices:
        return pd.Series(dtype=float, name=coin_id)

    ts = pd.DataFrame(prices, columns=["ts_ms", "price"])
    ts["date"] = pd.to_datetime(ts["ts_ms"], unit="ms", utc=True)
    ts = ts.set_index("date")["price"]
    ts = ts.resample("ME").last().dropna()
    ts.name = coin_id
    return ts


def build_returns_matrix(
    coin_ids: List[str],
    api_key: Optional[str] = None,
    months: int = ROLLING_WINDOW_MONTHS,
) -> pd.DataFrame:
    """Build a T × p DataFrame of monthly log-returns.

    Rows are month-end dates; columns are coin IDs.
    Only months with at least half the assets present are kept.
    """
    price_dict: Dict[str, pd.Series] = {}
    for cid in coin_ids:
        s = fetch_monthly_prices(cid, api_key, months)
        if len(s) >= 2:
            price_dict[cid] = s

    if not price_dict:
        return pd.DataFrame()

    prices = pd.DataFrame(price_dict)
    # keep rows where at least 50 % of assets have data
    prices = prices.dropna(thresh=max(1, len(prices.columns) // 2))
    log_returns = prices.apply(lambda col: (col / col.shift(1)).apply(
        lambda x: float("nan") if x <= 0 else __import__("math").log(x)
    )).dropna(how="all")
    return log_returns
