"""OnchainSensor — polls on-chain metrics and detects anomalies."""

import logging
import threading
import time
from typing import Any, Callable, Dict, Optional, Tuple

import requests

from config import (
    EXCHANGE_INFLOW_MULTIPLIER,
    GLASSNODE_BASE_URL,
    HASH_RATE_DROP_THRESHOLD,
    LIQUIDATION_ALERT_USD,
    ONCHAIN_SENSOR_INTERVAL_MINUTES,
    STABLECOIN_SUPPLY_CHANGE_PCT,
)

logger = logging.getLogger(__name__)

_COINGLASS_BASE = "https://open-api.coinglass.com/public/v2"


class OnchainSensor:
    """Monitors on-chain metrics: liquidations, exchange flows, hash rate, stablecoin supply."""

    def __init__(self, env: Dict[str, Any], risk_evaluator_callback: Optional[Callable] = None):
        self.env = env
        self._callback = risk_evaluator_callback
        self._glassnode_key = env.get("GLASSNODE_API_KEY")
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._prev_hash_rate: Optional[float] = None
        self._prev_stablecoin_supply: Optional[float] = None

    def start(self) -> None:
        self._running = True
        self._thread = threading.Thread(target=self._poll_loop, daemon=True, name="OnchainSensor")
        self._thread.start()
        logger.info("[OnchainSensor] Started (interval=%dm)", ONCHAIN_SENSOR_INTERVAL_MINUTES)

    def stop(self) -> None:
        self._running = False

    def _poll_loop(self) -> None:
        while self._running:
            try:
                score, details = self.scan()
                if score > 0.5 and self._callback:
                    self._callback("onchain", score, details)
            except Exception as exc:
                logger.error("[OnchainSensor] Poll error: %s", exc)
            time.sleep(ONCHAIN_SENSOR_INTERVAL_MINUTES * 60)

    def scan(self) -> Tuple[float, Dict]:
        """Run all on-chain checks and return (composite_score [0,1], details)."""
        details: Dict[str, Any] = {}
        scores = []

        # 1. Liquidations
        liq_score = self._check_liquidations(details)
        scores.append(liq_score)

        # 2. Exchange inflows (Glassnode BTC)
        inflow_score = self._check_exchange_inflows(details)
        scores.append(inflow_score)

        # 3. Hash rate drop
        hash_score = self._check_hash_rate(details)
        scores.append(hash_score)

        # 4. Stablecoin supply change
        stable_score = self._check_stablecoin_supply(details)
        scores.append(stable_score)

        composite = sum(scores) / len(scores) if scores else 0.0
        composite = max(0.0, min(1.0, composite))
        logger.debug("[OnchainSensor] composite=%.3f details=%s", composite, details)
        return composite, details

    def _check_liquidations(self, details: Dict) -> float:
        try:
            resp = requests.get(
                f"{_COINGLASS_BASE}/liquidation_chart",
                params={"time_type": "h4", "symbol": "BTC"},
                timeout=10,
            )
            if resp.status_code == 200:
                data = resp.json().get("data", [])
                if data:
                    recent = data[-1]
                    total_liq = float(recent.get("liquidationUsd", 0))
                    details["liquidation_usd"] = total_liq
                    if total_liq > LIQUIDATION_ALERT_USD:
                        return min(1.0, total_liq / LIQUIDATION_ALERT_USD / 2)
        except Exception as exc:
            logger.debug("Liquidation check error: %s", exc)
        return 0.0

    def _check_exchange_inflows(self, details: Dict) -> float:
        if not self._glassnode_key:
            return 0.0
        try:
            params = {
                "a": "BTC",
                "api_key": self._glassnode_key,
                "i": "24h",
            }
            resp = requests.get(
                f"{GLASSNODE_BASE_URL}/metrics/transactions/transfers_volume_to_exchanges_sum",
                params=params,
                timeout=15,
            )
            if resp.status_code == 200:
                data = resp.json()
                if len(data) >= 2:
                    recent = data[-1]["v"]
                    prev   = data[-2]["v"]
                    details["exchange_inflow_btc"] = recent
                    if prev > 0 and recent > prev * EXCHANGE_INFLOW_MULTIPLIER:
                        return min(1.0, recent / (prev * EXCHANGE_INFLOW_MULTIPLIER))
        except Exception as exc:
            logger.debug("Exchange inflow check error: %s", exc)
        return 0.0

    def _check_hash_rate(self, details: Dict) -> float:
        if not self._glassnode_key:
            return 0.0
        try:
            params = {"a": "BTC", "api_key": self._glassnode_key, "i": "24h"}
            resp = requests.get(
                f"{GLASSNODE_BASE_URL}/metrics/mining/hash_rate_mean",
                params=params,
                timeout=15,
            )
            if resp.status_code == 200:
                data = resp.json()
                if len(data) >= 2:
                    current = data[-1]["v"]
                    prev    = data[-2]["v"]
                    details["hash_rate"] = current
                    if prev > 0:
                        drop = (prev - current) / prev
                        if drop > HASH_RATE_DROP_THRESHOLD:
                            return min(1.0, drop / HASH_RATE_DROP_THRESHOLD)
        except Exception as exc:
            logger.debug("Hash rate check error: %s", exc)
        return 0.0

    def _check_stablecoin_supply(self, details: Dict) -> float:
        if not self._glassnode_key:
            return 0.0
        try:
            params = {"a": "USDT", "api_key": self._glassnode_key, "i": "24h"}
            resp = requests.get(
                f"{GLASSNODE_BASE_URL}/metrics/supply/current",
                params=params,
                timeout=15,
            )
            if resp.status_code == 200:
                data = resp.json()
                if len(data) >= 2:
                    current = data[-1]["v"]
                    prev    = data[-2]["v"]
                    details["stablecoin_supply"] = current
                    if prev > 0:
                        change_pct = abs((current - prev) / prev * 100)
                        if change_pct > STABLECOIN_SUPPLY_CHANGE_PCT:
                            return min(1.0, change_pct / STABLECOIN_SUPPLY_CHANGE_PCT)
        except Exception as exc:
            logger.debug("Stablecoin supply check error: %s", exc)
        return 0.0
