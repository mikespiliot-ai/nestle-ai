"""
DATA AGENT — Layer 0
Responsibilities:
  1. Maintain crypto universe (top 80 by mcap, no stablecoins)
  2. Fetch OHLCV: historical (60 months) + live prices
  3. Compute LLM-S features per asset (z-scored within rolling window)
  4. Fetch macro data: DXY, BTC dominance, Fear&Greed, VIX
  5. Causal masking: never leak future data
  6. Cache all data locally
"""

import os
import logging
import time
from datetime import datetime
from typing import Dict, List

import numpy as np
import pandas as pd
import requests

from config import (
    FEATURES,
    ROLLING_WINDOW_MONTHS,
    FRED_BASE_URL,
    GLASSNODE_BASE_URL,
    FEAR_GREED_URL,
)
from data.universe import fetch_universe, get_universe_ids
from data.historical import build_returns_matrix, fetch_monthly_prices
from data.live import get_current_prices, get_fear_greed_index, get_global_crypto_data
from memory.claude_flow_store import memory_store

logger = logging.getLogger(__name__)


class DataAgent:
    def __init__(self, env: dict):
        self.cg_key = env.get("COINGECKO_API_KEY", "")
        self.glassnode_key = env.get("GLASSNODE_API_KEY", "")
        self.fred_key = env.get("FRED_API_KEY", "")
        self.binance_key = env.get("BINANCE_API_KEY", "")

    # ── public entry point ──────────────────────────────────────────────────

    def run(self):
        logger.info("[DataAgent] Starting data collection cycle")

        universe = fetch_universe(api_key=self.cg_key)
        memory_store("universe_list", universe)
        logger.info("[DataAgent] Universe: %d coins", len(universe))

        coin_ids = get_universe_ids(universe)
        returns_df = build_returns_matrix(coin_ids, api_key=self.cg_key)
        price_history = {col: returns_df[col].dropna().tolist() for col in returns_df.columns}
        memory_store("price_history", price_history)
        logger.info("[DataAgent] Price history: %d assets, %d months", len(price_history), len(returns_df))

        features = self._compute_features(universe, returns_df)
        memory_store("features_matrix", features)
        logger.info("[DataAgent] Features computed for %d assets", len(features))

        macro = self._fetch_macro()
        memory_store("macro_data", macro)
        logger.info("[DataAgent] Macro data: %s", macro)

        logger.info("[DataAgent] Cycle complete")

    # ── feature engineering ─────────────────────────────────────────────────

    def _compute_features(self, universe: List[Dict], returns_df: pd.DataFrame) -> Dict:
        prices_now = get_current_prices(
            [c["id"] for c in universe], api_key=self.cg_key
        )

        raw: Dict[str, Dict] = {}
        for coin in universe:
            cid = coin["id"]
            sym = coin["symbol"]
            mcap = coin.get("market_cap", 0) or 0
            vol = coin.get("current_price", 0) * mcap if mcap > 0 else 0

            ret_series = returns_df.get(cid)
            mom30d = float(ret_series.iloc[-1]) if ret_series is not None and len(ret_series) > 0 else 0.0
            realized_vol = float(ret_series.std() * np.sqrt(12)) if ret_series is not None and len(ret_series) > 1 else 0.0

            nvt = self._fetch_nvt(cid, mcap)
            vol_to_mcap = vol / mcap if mcap > 0 else 0.0
            log_mcap = np.log(mcap) if mcap > 0 else 0.0

            raw[sym] = {
                "log_mcap": log_mcap,
                "vol_to_mcap": vol_to_mcap,
                "mom30d": mom30d,
                "nvt_ratio": nvt,
                "realized_vol": realized_vol,
                "coin_id": cid,
            }

        # Standardize each feature to z-scores across the current universe
        z_features: Dict[str, Dict] = {}
        for feature in FEATURES:
            vals = np.array([raw[sym][feature] for sym in raw if not np.isnan(raw[sym][feature])])
            mu = vals.mean() if len(vals) > 0 else 0.0
            sigma = vals.std() if len(vals) > 1 else 1.0
            sigma = sigma if sigma > 0 else 1.0
            for sym in raw:
                v = raw[sym][feature]
                z = (v - mu) / sigma if not np.isnan(v) else 0.0
                z_features.setdefault(sym, {})[f"{feature}_z"] = round(float(z), 4)

        # Merge raw + z-scored
        for sym in raw:
            z_features[sym].update({k: v for k, v in raw[sym].items() if k != "coin_id"})
            z_features[sym]["coin_id"] = raw[sym]["coin_id"]

        return z_features

    def _fetch_nvt(self, coin_id: str, market_cap: float) -> float:
        """
        Attempt to fetch NVT from Glassnode; fall back to market_cap / 1 if unavailable.
        Free-tier Glassnode only supports BTC/ETH for on-chain metrics.
        """
        if coin_id in ("bitcoin", "ethereum") and self.glassnode_key:
            asset = "BTC" if coin_id == "bitcoin" else "ETH"
            url = f"{GLASSNODE_BASE_URL}/metrics/transactions/transfers_volume_sum"
            params = {"a": asset, "api_key": self.glassnode_key, "i": "24h"}
            try:
                resp = requests.get(url, params=params, timeout=10)
                if resp.status_code == 200:
                    data = resp.json()
                    if data:
                        tx_vol = data[-1].get("v", 0) or 0
                        return market_cap / tx_vol if tx_vol > 0 else 0.0
            except Exception:
                pass
        # Fallback: use volume / mcap proxy
        return 0.0

    # ── macro data ──────────────────────────────────────────────────────────

    def _fetch_macro(self) -> Dict:
        fear_greed = get_fear_greed_index()
        global_data = get_global_crypto_data(api_key=self.cg_key)

        macro = {
            "fear_greed_index": fear_greed.get("value", 50),
            "fear_greed_class": fear_greed.get("classification", "Neutral"),
            "btc_dominance": global_data.get("btc_dominance", 0),
            "total_market_cap_usd": global_data.get("total_market_cap_usd", 0),
            "market_cap_change_24h": global_data.get("market_cap_change_24h", 0),
            "dxy": self._fetch_fred_series("DTWEXBGS"),
            "fed_funds_rate": self._fetch_fred_series("FEDFUNDS"),
            "vix": self._fetch_fred_series("VIXCLS"),
            "timestamp": datetime.utcnow().isoformat(),
        }
        return macro

    def _fetch_fred_series(self, series_id: str) -> float:
        if not self.fred_key:
            return 0.0
        url = f"{FRED_BASE_URL}/series/observations"
        params = {
            "series_id": series_id,
            "api_key": self.fred_key,
            "file_type": "json",
            "limit": 1,
            "sort_order": "desc",
        }
        try:
            resp = requests.get(url, params=params, timeout=10)
            resp.raise_for_status()
            obs = resp.json().get("observations", [])
            if obs:
                val = obs[0].get("value", ".")
                return float(val) if val != "." else 0.0
        except Exception as e:
            logger.debug("FRED fetch failed for %s: %s", series_id, e)
        return 0.0
