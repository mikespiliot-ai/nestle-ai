"""RiskEvaluator — aggregates sensor scores and triggers emergency actions."""

import json
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, Optional

from config import (
    EMERGENCY_COOLDOWN_HOURS,
    EMERGENCY_DEFENSIVE_THRESHOLD,
    EMERGENCY_HEDGE_THRESHOLD,
    EMERGENCY_MACRO_WEIGHT,
    EMERGENCY_ONCHAIN_WEIGHT,
    EMERGENCY_REDUCE_THRESHOLD,
    EMERGENCY_SOCIAL_WEIGHT,
    EMERGENCY_TRIGGER_SCORE,
    LOGS_DIR,
)

logger = logging.getLogger(__name__)


class RiskEvaluator:
    """Receives sensor events, computes composite emergency score, triggers actions."""

    def __init__(self, backtest_agent_fn: Callable):
        self._agent_fn = backtest_agent_fn
        self._scores: Dict[str, float] = {"macro": 0.0, "onchain": 0.0, "social": 0.0}
        self._last_action_time: Optional[datetime] = None
        self._current_mode = "NORMAL"

    # ── Public API ────────────────────────────────────────────────────────────

    def on_sensor_event(self, source: str, score: float, details: Any) -> None:
        """Called by sensors when they detect anomalies."""
        if source in ("macro",):
            self._scores["macro"] = max(0.0, min(1.0, score))
        elif source == "onchain":
            self._scores["onchain"] = max(0.0, min(1.0, score))
        elif source in ("social_panic", "social_fomo"):
            self._scores["social"] = max(0.0, min(1.0, score))

        composite = self._compute_composite()
        logger.info(
            "[RiskEvaluator] composite=%.3f macro=%.3f onchain=%.3f social=%.3f",
            composite, self._scores["macro"], self._scores["onchain"], self._scores["social"],
        )

        if composite >= EMERGENCY_TRIGGER_SCORE and self._cooldown_ok():
            action = self._determine_action(composite)
            self._execute(action, composite, details)
            self._last_action_time = datetime.now(timezone.utc)
            self._current_mode = action

    def check_recovery(self) -> bool:
        """Check if we can exit defensive mode (scores have normalized)."""
        if self._current_mode == "NORMAL":
            return True
        composite = self._compute_composite()
        if composite < EMERGENCY_TRIGGER_SCORE * 0.7:
            logger.info("[RiskEvaluator] Recovery detected — returning to NORMAL mode")
            self._current_mode = "NORMAL"
            return True
        return False

    # ── Internals ─────────────────────────────────────────────────────────────

    def _compute_composite(self) -> float:
        return (
            EMERGENCY_MACRO_WEIGHT   * self._scores["macro"]
            + EMERGENCY_ONCHAIN_WEIGHT * self._scores["onchain"]
            + EMERGENCY_SOCIAL_WEIGHT  * self._scores["social"]
        )

    def _cooldown_ok(self) -> bool:
        if self._last_action_time is None:
            return True
        elapsed = datetime.now(timezone.utc) - self._last_action_time
        return elapsed > timedelta(hours=EMERGENCY_COOLDOWN_HOURS)

    def _determine_action(self, composite: float) -> str:
        if composite >= EMERGENCY_DEFENSIVE_THRESHOLD:
            return "DEFENSIVE"
        elif composite >= EMERGENCY_REDUCE_THRESHOLD:
            return "REDUCE"
        else:
            return "HEDGE"

    def _execute(self, action: str, score: float, details: Any) -> None:
        logger.warning("[RiskEvaluator] Executing emergency action: %s (score=%.3f)", action, score)
        try:
            agent = self._agent_fn()
            price_map = {}  # agent will use cached prices
            agent.run_emergency_action(action, price_map)
        except Exception as exc:
            logger.error("[RiskEvaluator] Emergency execution error: %s", exc)
        self._log_event(action, score, details)

    def _log_event(self, action: str, score: float, details: Any) -> None:
        os.makedirs(LOGS_DIR, exist_ok=True)
        ts = datetime.now(timezone.utc).isoformat()
        event = {
            "timestamp": ts,
            "action": action,
            "composite_score": score,
            "sensor_scores": dict(self._scores),
            "details": details,
        }
        fname = os.path.join(LOGS_DIR, f"emergency_{ts[:10]}_{action}.json")
        try:
            with open(fname, "w") as fh:
                json.dump(event, fh, indent=2, default=str)
        except Exception as exc:
            logger.error("Event log write error: %s", exc)
