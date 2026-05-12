"""
CONSENSUS AGENT — Layer 2
Implements paper Section 5.2.1 intersection rule.
Combines LLM-S and Sentiment signals with macro overlay.
"""

import logging
from typing import Dict, List, Set, Tuple

from config import (
    TARGET_PORTFOLIO_SIZE,
    MACRO_REDUCE_THRESHOLD,
)
from memory.claude_flow_store import memory_store, memory_retrieve

logger = logging.getLogger(__name__)


class ConsensusAgent:
    def run(self):
        logger.info("[ConsensusAgent] Computing consensus")

        s1 = memory_retrieve("s1_signals", {"buys": [], "sells": []})
        s2 = memory_retrieve("s2_signals", {"buys": [], "sells": []})
        s1_strengths: Dict[str, float] = memory_retrieve("s1_strengths", {})
        s2_scores: Dict[str, float] = memory_retrieve("s2_scores", {})
        macro_score: float = memory_retrieve("macro_score", 0.0)

        s1_buys = set(s1["buys"])
        s1_sells = set(s1["sells"])
        s2_buys = set(s2["buys"])
        s2_sells = set(s2["sells"])

        final_buys, final_sells = self._consensus_rule(s1_buys, s2_buys, s1_sells, s2_sells)

        # Macro overlay: tighten buy list if risk-off
        if macro_score < MACRO_REDUCE_THRESHOLD:
            logger.info("[ConsensusAgent] Macro overlay: tightening buy list (score=%.2f)", macro_score)
            combined_strength = {
                sym: 0.5 * s1_strengths.get(sym, 0.0) + 0.5 * abs(s2_scores.get(sym, 0.0))
                for sym in final_buys
            }
            final_buys = {sym for sym, st in combined_strength.items() if st > 0.7}

        # Select top TARGET_PORTFOLIO_SIZE by combined signal strength
        combined_strength = {
            sym: 0.5 * s1_strengths.get(sym, 0.0) + 0.5 * abs(s2_scores.get(sym, 0.0))
            for sym in final_buys
        }
        selected = sorted(combined_strength, key=lambda x: combined_strength[x], reverse=True)
        selected = selected[:TARGET_PORTFOLIO_SIZE]

        logger.info("[ConsensusAgent] Selected %d assets", len(selected))
        memory_store("selected_universe", selected)
        memory_store("consensus_sells", list(final_sells))

    # ── paper consensus rule ─────────────────────────────────────────────────

    @staticmethod
    def _consensus_rule(
        s1_buys: Set[str], s2_buys: Set[str],
        s1_sells: Set[str], s2_sells: Set[str],
    ) -> Tuple[Set[str], Set[str]]:
        buy_intersection = s1_buys & s2_buys
        sell_intersection = s1_sells & s2_sells

        final_buys = buy_intersection if len(buy_intersection) > 1 else (s1_buys | s2_buys)
        final_sells = sell_intersection if len(sell_intersection) > 1 else (s1_sells | s2_sells)

        conflicts = final_buys & final_sells
        final_buys -= conflicts
        final_sells -= conflicts

        return final_buys, final_sells
