"""
RISK EVALUATOR — Event-driven, triggered by sensors.
Computes composite emergency score and determines action.
Enforces 48-hour cooldown between emergency rebalances.
"""

import json
import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict

from config import (
    EMERGENCY_TRIGGER_SCORE,
    EMERGENCY_COOLDOWN_HOURS,
    EMERGENCY_MACRO_WEIGHT,
    EMERGENCY_ONCHAIN_WEIGHT,
    EMERGENCY_SOCIAL_WEIGHT,
    EMERGENCY_DEFENSIVE_THRESHOLD,
    EMERGENCY_REDUCE_THRESHOLD,
    EMERGENCY_HEDGE_THRESHOLD,
    LOGS_DIR,
)
from memory.claude_flow_store import memory_store, memory_retrieve, memory_append

logger = logging.getLogger(__name__)


class RiskEvaluator:
    def __init__(self, backtest_agent_fn):
        """
        backtest_agent_fn: callable(action: str, price_map: Dict)
        """
        self._execute = backtest_agent_fn
        os.makedirs(LOGS_DIR, exist_ok=True)

    # ── callback triggered by sensors ───────────────────────────────────────

    def on_sensor_event(self, source: str, sensor_score: float, details: Any):
        logger.info("[RiskEvaluator] Event from %s: score=%.3f", source, sensor_score)

        macro_s = abs(memory_retrieve("macro_sensor_score", 0.0))
        onchain_s = memory_retrieve("onchain_sensor_score", 0.0)
        social_s = memory_retrieve("social_panic_score", 0.0)

        emergency_score = (
            EMERGENCY_MACRO_WEIGHT * macro_s
            + EMERGENCY_ONCHAIN_WEIGHT * onchain_s
            + EMERGENCY_SOCIAL_WEIGHT * social_s
        )
        memory_store("emergency_score", emergency_score)
        logger.info("[RiskEvaluator] Composite emergency_score=%.4f", emergency_score)

        if emergency_score < EMERGENCY_TRIGGER_SCORE:
            logger.info("[RiskEvaluator] Below trigger threshold — no action")
            return

        if not self._cooldown_ok():
            logger.info("[RiskEvaluator] Cooldown active — skipping emergency rebalance")
            return

        action = self._determine_action(emergency_score)
        logger.warning("[RiskEvaluator] EMERGENCY ACTION: %s (score=%.4f)", action, emergency_score)

        # Execute action through backtest agent
        price_map = memory_retrieve("live_prices", {})
        try:
            self._execute(action, price_map)
        except Exception as e:
            logger.error("[RiskEvaluator] Execution failed: %s", e)
            return

        # Log the event
        event_log = {
            "timestamp": datetime.utcnow().isoformat(),
            "source": source,
            "emergency_score": emergency_score,
            "action": action,
            "macro_score": macro_s,
            "onchain_score": onchain_s,
            "social_score": social_s,
            "details": str(details),
        }
        memory_store("last_emergency", datetime.utcnow().isoformat())
        memory_append("emergency_log", event_log)

        log_path = os.path.join(
            LOGS_DIR,
            f"emergency_{datetime.utcnow().strftime('%Y_%m_%d_%H')}.json",
        )
        with open(log_path, "w") as f:
            json.dump(event_log, f, indent=2, default=str)

        self._generate_alert_report(event_log)

    # ── recovery check ───────────────────────────────────────────────────────

    def check_recovery(self):
        """
        Check if portfolio in defensive mode should return to normal.
        Called during the monthly cycle.
        """
        portfolio_state = memory_retrieve("portfolio_state", {})
        is_defensive = portfolio_state.get("mode") == "DEFENSIVE"
        emergency_score = memory_retrieve("emergency_score", 0.0)

        if is_defensive and emergency_score < 0.30:
            logger.info("[RiskEvaluator] Recovery: conditions normalized — triggering rebalance")
            memory_store("force_rebalance", True)

    # ── internals ────────────────────────────────────────────────────────────

    def _cooldown_ok(self) -> bool:
        last = memory_retrieve("last_emergency")
        if last is None:
            return True
        try:
            last_dt = datetime.fromisoformat(last)
            return datetime.utcnow() - last_dt > timedelta(hours=EMERGENCY_COOLDOWN_HOURS)
        except Exception:
            return True

    @staticmethod
    def _determine_action(score: float) -> str:
        if score >= EMERGENCY_DEFENSIVE_THRESHOLD:
            return "DEFENSIVE"
        if score >= EMERGENCY_REDUCE_THRESHOLD:
            return "REDUCE"
        return "HEDGE"

    def _generate_alert_report(self, event: Dict):
        from reports.dashboard import generate_alert_html
        try:
            generate_alert_html(event)
        except Exception as e:
            logger.debug("Alert report generation failed: %s", e)
