"""Fetch and manage the crypto trading universe."""

import logging
from typing import Any, Dict, List, Optional

import requests

from config import (
    COINGECKO_BASE_URL,
    CRYPTO_UNIVERSE_SIZE,
    STABLECOIN_LIST,
)

logger = logging.getLogger(__name__)


def fetch_universe(api_key: Optional[str] = None) -> List[Dict[str, Any]]:
    """Fetch the top *CRYPTO_UNIVERSE_SIZE* coins from CoinGecko.

    Excludes stablecoins.  Returns a list of dicts with keys:
    ``id``, ``symbol``, ``name``, ``market_cap``, ``current_price``, ``rank``.
    """
    headers = {}
    if api_key:
        headers["x-cg-pro-api-key"] = api_key

    coins: List[Dict[str, Any]] = []
    page = 1
    per_page = 250  # fetch a generous page and filter

    while len(coins) < CRYPTO_UNIVERSE_SIZE:
        params = {
            "vs_currency": "usd",
            "order": "market_cap_desc",
            "per_page": per_page,
            "page": page,
            "sparkline": "false",
        }
        try:
            resp = requests.get(
                f"{COINGECKO_BASE_URL}/coins/markets",
                params=params,
                headers=headers,
                timeout=30,
            )
            resp.raise_for_status()
            batch = resp.json()
        except Exception as exc:
            logger.error("CoinGecko /coins/markets error (page %d): %s", page, exc)
            break

        if not batch:
            break

        for coin in batch:
            coin_id = coin.get("id", "")
            symbol  = coin.get("symbol", "").lower()
            if coin_id in STABLECOIN_LIST or symbol in STABLECOIN_LIST:
                continue
            coins.append(
                {
                    "id":            coin_id,
                    "symbol":        symbol,
                    "name":          coin.get("name", ""),
                    "market_cap":    coin.get("market_cap", 0) or 0,
                    "current_price": coin.get("current_price", 0) or 0,
                    "rank":          coin.get("market_cap_rank", 9999) or 9999,
                }
            )
            if len(coins) >= CRYPTO_UNIVERSE_SIZE:
                break

        page += 1
        if page > 10:
            break  # safety guard

    logger.info("Universe fetched: %d coins", len(coins))
    return coins[:CRYPTO_UNIVERSE_SIZE]


def get_universe_symbols(api_key: Optional[str] = None) -> List[str]:
    """Return a list of ticker symbols for the universe."""
    return [c["symbol"] for c in fetch_universe(api_key)]


def get_universe_ids(api_key: Optional[str] = None) -> List[str]:
    """Return a list of CoinGecko IDs for the universe."""
    return [c["id"] for c in fetch_universe(api_key)]
