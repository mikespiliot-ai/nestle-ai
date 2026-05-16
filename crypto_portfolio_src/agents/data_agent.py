"""DataAgent — fetches universe, builds returns matrix, computes features and macro data."""

import logging
import math
import os
from typing import Any, Dict, Optional

import numpy as np
import requests

from config import (
    FEATURES,
    FRED_BASE_URL,
    ROLLING_WINDOW_MONTHS,
)
from data.universe import fetch_universe
from data.historical import build_returns_matrix
from data.live import get_fear_greed_index, get_global_crypto_data
from memory.claude_flow_store import memory_store

logger = logging.getLogger(__name__)


class DataAgent:
    """Fetches all market data and stores it in the shared memory store."""

    def __init__(self, env: Dict[str, Any]):
        self.env = env
        self.api_key = env.get("COINGECKO_API_KEY")
        self.fred_key = env.get("FRED_API_KEY")

    # ── Public entry point ────────────────────────────────────────────────────

    def run(self) -> None:
        logger.info("[DataAgent] Starting data fetch cycle…")

        # 1. Universe
        universe = fetch_universe(self.api_key)
        memory_store("universe", universe)
        coin_ids = [c["id"] for c in universe]
        memory_store("coin_ids", coin_ids)
        logger.info("[DataAgent] Universe: %d coins", len(universe))

        # 2. Returns matrix
        R = build_returns_matrix(coin_ids, self.api_key, ROLLING_WINDOW_MONTHS)
        memory_store("returns_matrix", R.to_dict() if not R.empty else {})
        logger.info("[DataAgent] Returns matrix: %s", R.shape)

        # 3. Z-scored features
        features = self._compute_features(universe, R)
        memory_store("features", features)
        logger.info("[DataAgent] Features computed for %d assets", len(features))

        # 4. Macro data
        macro = self._fetch_macro()
        memory_store("macro_data", macro)
        logger.info("[DataAgent] Macro data fetched")

    # ── Feature engineering ───────────────────────────────────────────────────

    def _compute_features(
        self, universe: list, R: "pd.DataFrame"
    ) -> Dict[str, Dict[str, float]]:
        """Compute and z-score FEATURES for each asset."""
        import pandas as pd

        raw: Dict[str, Dict[str, float]] = {}

        for coin in universe:
            cid = coin["id"]
            mcap = coin.get("market_cap", 0) or 0
            vol = coin.get("current_price", 0) or 0  # price proxy for vol_to_mcap
            log_mcap = math.log(mcap) if mcap > 0 else 0.0
            vol_to_mcap = vol / mcap if mcap > 0 else 0.0

            # Momentum: last 30 days from returns matrix
            mom30d = 0.0
            if not R.empty and cid in R.columns:
                series = R[cid].dropna()
                if len(series) >= 1:
                    mom30d = float(series.iloc[-1])

            # NVT proxy (we don't have on-chain volume, use 0)
            nvt_ratio = 0.0

            # Realized vol: std of last 12 months
            realized_vol = 0.0
            if not R.empty and cid in R.columns:
                series = R[cid].dropna()
                if len(series) >= 2:
                    realized_vol = float(series.tail(12).std())

            raw[cid] = {
                "log_mcap":    log_mcap,
                "vol_to_mcap": vol_to_mcap,
                "mom30d":      mom30d,
                "nvt_ratio":   nvt_ratio,
                "realized_vol": realized_vol,
            }

        if not raw:
            return {}

        # Z-score each feature cross-sectionally
        feature_arrays: Dict[str, list] = {f: [] for f in FEATURES}
        ids_list = list(raw.keys())
        for cid in ids_list:
            for feat in FEATURES:
                feature_arrays[feat].append(raw[cid][feat])

        z_features: Dict[str, Dict[str, float]] = {cid: {} for cid in ids_list}
        for feat in FEATURES:
            arr = np.array(feature_arrays[feat], dtype=float)
            mean = np.nanmean(arr)
            std  = np.nanstd(arr)
            if std < 1e-12:
                z_arr = np.zeros_like(arr)
            else:
                z_arr = (arr - mean) / std
            for i, cid in enumerate(ids_list):
                z_features[cid][feat] = float(z_arr[i])

        return z_features

    # ── Macro data ────────────────────────────────────────────────────────────

    def _fetch_macro(self) -> Dict[str, Any]:
        macro: Dict[str, Any] = {}

        # Fear & Greed
        fg = get_fear_greed_index()
        macro["fear_greed"] = fg

        # Global crypto
        gc = get_global_crypto_data(self.api_key)
        macro["global_crypto"] = gc

        # FRED series
        if self.fred_key:
            for series_id in ["DTWEXBGS", "FEDFUNDS", "VIXCLS"]:
                val = self._fetch_fred(series_id)
                macro[series_id] = val

        return macro

    def _fetch_fred(self, series_id: str) -> Optional[float]:
        try:
            params = {
                "series_id": series_id,
                "api_key":   self.fred_key,
                "file_type": "json",
                "sort_order": "desc",
                "limit": 1,
            }
            resp = requests.get(
                f"{FRED_BASE_URL}/series/observations",
                params=params,
                timeout=15,
            )
            resp.raise_for_status()
            obs = resp.json().get("observations", [])
            if obs:
                val = obs[0].get("value", ".")
                return float(val) if val != "." else None
        except Exception as exc:
            logger.warning("FRED %s error: %s", series_id, exc)
        return None
