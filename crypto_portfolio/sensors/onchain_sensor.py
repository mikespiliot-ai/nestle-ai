"""
ONCHAIN SENSOR — Polls every 30 minutes.
Monitors exchange flows, whale movements, liquidations, stablecoin supply, hash rate.
"""

import logging
import time
from datetime import datetime
from typing import Dict, Tuple

import requests

from config import (
    ONCHAIN_SENSOR_INTERVAL_MINUTES,
    EXCHANGE_INFLOW_MULTIPLIER,
    WHALE_TRANSFER_BTC_THRESHOLD,
    LIQUIDATION_ALERT_USD,
    STABLECOIN_SUPPLY_CHANGE_PCT,
    HASH_RATE_DROP_THRESHOLD,
    GLASSNODE_BASE_URL,
)
from memory.claude_flow_store import memory_store

logger = logging.getLogger(__name__)


class OnchainSensor:
    def __init__(self, env: dict):
        self.glassnode_key = env.get("GLASSNODE_API_KEY", "")
        self._interval = ONCHAIN_SENSOR_INTERVAL_MINUTES * 60

    def start(self, risk_evaluator_callback):
        logger.info("[OnchainSensor] Starting (interval=%dm)", ONCHAIN_SENSOR_INTERVAL_MINUTES)
        while True:
            try:
                score, details = self.poll()
                memory_store("onchain_sensor_score", score)
                memory_store("onchain_sensor_details", details)
                if score > 0.5:
                    logger.warning("[OnchainSensor] Alert: score=%.3f", score)
                    risk_evaluator_callback("onchain", score, details)
            except Exception as e:
                logger.error("[OnchainSensor] Poll error: %s", e)
            time.sleep(self._interval)

    def poll(self) -> Tuple[float, Dict]:
        score = 0.0
        details: Dict = {}

        liquidation_score, liq_info = self._check_liquidations()
        score += liquidation_score * 0.35
        details["liquidations"] = liq_info

        if self.glassnode_key:
            exflow_score, exflow_info = self._check_exchange_flows()
            score += exflow_score * 0.30
            details["exchange_flows"] = exflow_info

            hr_score, hr_info = self._check_hash_rate()
            score += hr_score * 0.20
            details["hash_rate"] = hr_info

            stable_score, stable_info = self._check_stablecoin_supply()
            score = score - stable_score * 0.15  # positive = bullish, reduce alert
            details["stablecoin"] = stable_info
        else:
            details["note"] = "Glassnode key not configured — limited onchain data"

        score = max(0.0, min(1.0, score))
        return score, details

    # ── individual checks ────────────────────────────────────────────────────

    def _check_liquidations(self) -> Tuple[float, Dict]:
        try:
            resp = requests.get(
                "https://open-api.coinglass.com/public/v2/liquidation_history",
                params={"time_type": "h1", "symbol": "ALL"},
                timeout=10,
            )
            if resp.status_code == 200:
                data = resp.json().get("data", {})
                total = data.get("totalLiquidationsUsd", 0)
                if total > LIQUIDATION_ALERT_USD:
                    score = min(1.0, total / (LIQUIDATION_ALERT_USD * 2))
                    return score, {"total_usd": total, "alert": True}
        except Exception:
            pass
        return 0.0, {"alert": False}

    def _check_exchange_flows(self) -> Tuple[float, Dict]:
        url = f"{GLASSNODE_BASE_URL}/metrics/transactions/transfers_to_exchanges_sum"
        params = {"a": "BTC", "api_key": self.glassnode_key, "i": "24h"}
        try:
            resp = requests.get(url, params=params, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                if len(data) >= 30:
                    recent = data[-1].get("v", 0)
                    avg_30d = sum(d.get("v", 0) for d in data[-30:]) / 30
                    if avg_30d > 0 and recent > EXCHANGE_INFLOW_MULTIPLIER * avg_30d:
                        score = min(1.0, (recent / avg_30d) / 4.0)
                        return score, {"recent": recent, "avg_30d": avg_30d, "alert": True}
        except Exception as e:
            logger.debug("Exchange flow check failed: %s", e)
        return 0.0, {"alert": False}

    def _check_hash_rate(self) -> Tuple[float, Dict]:
        url = f"{GLASSNODE_BASE_URL}/metrics/mining/hash_rate_mean"
        params = {"a": "BTC", "api_key": self.glassnode_key, "i": "24h"}
        try:
            resp = requests.get(url, params=params, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                if len(data) >= 7:
                    current = data[-1].get("v", 1)
                    week_ago = data[-7].get("v", current)
                    drop = (week_ago - current) / week_ago if week_ago > 0 else 0
                    if drop > HASH_RATE_DROP_THRESHOLD:
                        return min(1.0, drop * 3), {"drop_pct": drop * 100, "alert": True}
        except Exception as e:
            logger.debug("Hash rate check failed: %s", e)
        return 0.0, {"alert": False}

    def _check_stablecoin_supply(self) -> Tuple[float, Dict]:
        # Positive stablecoin inflow → bullish (new money entering)
        url = f"{GLASSNODE_BASE_URL}/metrics/supply/current"
        params = {"a": "USDT", "api_key": self.glassnode_key, "i": "24h"}
        try:
            resp = requests.get(url, params=params, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                if len(data) >= 2:
                    now_v = data[-1].get("v", 0)
                    prev_v = data[-2].get("v", now_v)
                    change_pct = abs((now_v - prev_v) / prev_v * 100) if prev_v > 0 else 0
                    if change_pct > STABLECOIN_SUPPLY_CHANGE_PCT:
                        direction = "increase" if now_v > prev_v else "decrease"
                        bullish = now_v > prev_v
                        return (0.5 if bullish else -0.3), {
                            "change_pct": change_pct,
                            "direction": direction,
                        }
        except Exception as e:
            logger.debug("Stablecoin check failed: %s", e)
        return 0.0, {}
