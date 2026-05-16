"""MacroAgent — computes macro regime score and sets macro_regime."""

import logging
from typing import Any, Dict

from config import (
    MACRO_DEFENSIVE_THRESHOLD,
    MACRO_REDUCE_THRESHOLD,
    VIX_RISK_OFF_LEVEL,
)
from memory.claude_flow_store import memory_retrieve, memory_store

logger = logging.getLogger(__name__)


class MacroAgent:
    """Computes a macro score in [-1, +1] and sets macro_regime."""

    def __init__(self, env: Dict[str, Any] = None):
        self.env = env or {}

    def run(self) -> None:
        logger.info("[MacroAgent] Computing macro regime…")

        macro_data: Dict[str, Any] = memory_retrieve("macro_data", {})
        score = self._compute_macro_score(macro_data)
        regime = self._determine_regime(score)

        memory_store("macro_score", score)
        memory_store("macro_regime", regime)
        logger.info("[MacroAgent] score=%.3f regime=%s", score, regime)

    # ── Score computation ─────────────────────────────────────────────────────

    def _compute_macro_score(self, macro_data: Dict[str, Any]) -> float:
        """Aggregate macro indicators into a single score in [-1, +1]."""
        scores = []
        weights = []

        # Fear & Greed index [0-100]: normalize to [-1, +1]
        fg = macro_data.get("fear_greed", {})
        if fg:
            fg_val = fg.get("value", 50)
            fg_score = (fg_val - 50) / 50.0  # [-1, +1]
            scores.append(fg_score)
            weights.append(0.25)

        # Global crypto data
        gc = macro_data.get("global_crypto", {})
        if gc:
            # BTC dominance: high dominance = risk-off, bearish for alts
            btc_dom = gc.get("btc_dominance", 50)
            btc_score = -(btc_dom - 50) / 50.0  # high dominance → negative
            scores.append(btc_score)
            weights.append(0.15)

            # 24h market cap change
            mcap_chg = gc.get("market_cap_change_24h_pct", 0)
            mcap_score = max(-1.0, min(1.0, mcap_chg / 10.0))
            scores.append(mcap_score)
            weights.append(0.20)

        # VIX (VIXCLS from FRED)
        vix = macro_data.get("VIXCLS")
        if vix is not None:
            if vix >= VIX_RISK_OFF_LEVEL:
                vix_score = -min(1.0, (vix - VIX_RISK_OFF_LEVEL) / 20.0)
            else:
                vix_score = min(1.0, (VIX_RISK_OFF_LEVEL - vix) / 20.0) * 0.5
            scores.append(vix_score)
            weights.append(0.25)

        # Fed Funds Rate — higher = tighter conditions
        fedfunds = macro_data.get("FEDFUNDS")
        if fedfunds is not None:
            ff_score = -min(1.0, fedfunds / 10.0)
            scores.append(ff_score)
            weights.append(0.15)

        if not scores:
            return 0.0

        total_weight = sum(weights)
        weighted = sum(s * w for s, w in zip(scores, weights))
        return max(-1.0, min(1.0, weighted / total_weight))

    def _determine_regime(self, score: float) -> str:
        if score <= MACRO_DEFENSIVE_THRESHOLD:
            return "DEFENSIVE"
        elif score <= MACRO_REDUCE_THRESHOLD:
            return "REDUCE"
        else:
            return "NORMAL"
