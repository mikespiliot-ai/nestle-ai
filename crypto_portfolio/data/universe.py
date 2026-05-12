"""
Crypto universe management.
Fetches top-N coins by market cap, excludes stablecoins, and caches the list.
"""

import time
import logging
import requests
from typing import List, Dict

from config import (
    COINGECKO_BASE_URL,
    CRYPTO_UNIVERSE_SIZE,
    EXCLUDE_STABLECOINS,
    STABLECOIN_LIST,
    COINGECKO_CALLS_PER_MIN,
)

logger = logging.getLogger(__name__)

_RATE_DELAY = 60.0 / COINGECKO_CALLS_PER_MIN


def fetch_universe(api_key: str = "") -> List[Dict]:
    """
    Fetch the top CRYPTO_UNIVERSE_SIZE coins by market cap from CoinGecko.
    Returns list of dicts with id, symbol, name, market_cap, current_price.
    """
    headers = {}
    if api_key:
        headers["x-cg-demo-api-key"] = api_key

    coins = []
    per_page = 250
    page = 1

    while len(coins) < CRYPTO_UNIVERSE_SIZE:
        url = f"{COINGECKO_BASE_URL}/coins/markets"
        params = {
            "vs_currency": "usd",
            "order": "market_cap_desc",
            "per_page": per_page,
            "page": page,
            "sparkline": False,
        }
        try:
            resp = requests.get(url, params=params, headers=headers, timeout=30)
            resp.raise_for_status()
            batch = resp.json()
        except requests.RequestException as e:
            logger.error("CoinGecko universe fetch failed: %s", e)
            break

        if not batch:
            break

        for coin in batch:
            symbol = coin.get("symbol", "").upper()
            if EXCLUDE_STABLECOINS and symbol in STABLECOIN_LIST:
                continue
            coins.append({
                "id": coin["id"],
                "symbol": symbol,
                "name": coin["name"],
                "market_cap": coin.get("market_cap", 0),
                "current_price": coin.get("current_price", 0),
                "rank": coin.get("market_cap_rank", 9999),
            })
            if len(coins) >= CRYPTO_UNIVERSE_SIZE:
                break

        page += 1
        time.sleep(_RATE_DELAY)

    logger.info("Universe: %d coins loaded", len(coins))
    return coins[:CRYPTO_UNIVERSE_SIZE]


def get_universe_symbols(coins: List[Dict]) -> List[str]:
    return [c["symbol"] for c in coins]


def get_universe_ids(coins: List[Dict]) -> List[str]:
    return [c["id"] for c in coins]
