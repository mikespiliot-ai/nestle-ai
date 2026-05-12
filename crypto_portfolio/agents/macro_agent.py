"""
MACRO AGENT — Global context scoring.
Combines DXY, Fed rate direction, VIX, BTC dominance, total market cap trend,
and regulatory news into a single macro_score in [-1.0, +1.0].
"""

import logging
from typing import Dict

from config import (
    VIX_RISK_OFF_LEVEL,
    MACRO_REDUCE_THRESHOLD,
    MACRO_DEFENSIVE_THRESHOLD,
    MACRO_REDUCE_FRACTION,
)
from memory.claude_flow_store import memory_store, memory_retrieve

logger = logging.getLogger(__name__)


class MacroAgent:
    def run(self):
        logger.info("[MacroAgent] Computing macro score")

        macro_data: Dict = memory_retrieve("macro_data", {})

        score = self._compute_score(macro_data)
        logger.info("[MacroAgent] macro_score=%.3f", score)
        memory_store("macro_score", score)

        if score < MACRO_DEFENSIVE_THRESHOLD:
            memory_store("macro_regime", "DEFENSIVE")
            logger.warning("[MacroAgent] DEFENSIVE regime triggered (score=%.2f)", score)
        elif score < MACRO_REDUCE_THRESHOLD:
            memory_store("macro_regime", "REDUCE")
            logger.warning("[MacroAgent] REDUCE regime triggered (score=%.2f)", score)
        else:
            memory_store("macro_regime", "NORMAL")

    # ── scoring ─────────────────────────────────────────────────────────────

    def _compute_score(self, macro: Dict) -> float:
        components = []

        # VIX — high VIX = risk-off
        vix = macro.get("vix", 20)
        if vix > 0:
            vix_score = max(-1.0, 1.0 - vix / VIX_RISK_OFF_LEVEL)
            components.append(vix_score * 0.25)

        # Fear & Greed Index (0-100 → map to -1 to +1)
        fg = macro.get("fear_greed_index", 50)
        fg_score = (fg - 50) / 50.0
        components.append(fg_score * 0.25)

        # BTC dominance trend: rising dominance = risk-off (altcoins sell)
        btc_dom = macro.get("btc_dominance", 50)
        btc_dom_score = (50 - btc_dom) / 50.0  # positive when BTC dom < 50%
        components.append(btc_dom_score * 0.15)

        # Total market cap change 24h
        mcap_change = macro.get("market_cap_change_24h", 0)
        mcap_score = max(-1.0, min(1.0, mcap_change / 10.0))  # normalize to ±1
        components.append(mcap_score * 0.20)

        # Fed funds rate: high rate = bearish (penalize > 4%)
        fed_rate = macro.get("fed_funds_rate", 2.5)
        if fed_rate > 4.0:
            rate_score = -0.6
        elif fed_rate > 2.5:
            rate_score = -0.2
        else:
            rate_score = 0.2
        components.append(rate_score * 0.15)

        total = sum(components) if components else 0.0
        return round(max(-1.0, min(1.0, total)), 4)
