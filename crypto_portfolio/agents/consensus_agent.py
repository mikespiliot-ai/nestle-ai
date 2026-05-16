"""ConsensusAgent — combines S1 and S2 signals into a final buy/sell list."""

import logging
from typing import Any, Dict, List, Set, Tuple

from config import TARGET_PORTFOLIO_SIZE
from memory.claude_flow_store import memory_retrieve, memory_store

logger = logging.getLogger(__name__)


class ConsensusAgent:
    """Merges crypto signal and sentiment signals, applies macro overlay."""

    def __init__(self, env: Dict[str, Any] = None):
        self.env = env or {}

    def run(self) -> None:
        logger.info("[ConsensusAgent] Building consensus…")

        s1_signals: Dict[str, str]  = memory_retrieve("s1_signals", {})
        s1_strengths: Dict[str, float] = memory_retrieve("s1_strengths", {})
        s2_signals: Dict[str, str]  = memory_retrieve("s2_signals", {})
        s2_scores: Dict[str, float] = memory_retrieve("s2_scores", {})
        macro_regime: str = memory_retrieve("macro_regime", "NORMAL")

        all_ids = set(s1_signals) | set(s2_signals)

        s1_buys  = {k for k in all_ids if s1_signals.get(k) == "BUY"}
        s1_sells = {k for k in all_ids if s1_signals.get(k) == "SELL"}
        s2_buys  = {k for k in all_ids if s2_signals.get(k) == "BUY"}
        s2_sells = {k for k in all_ids if s2_signals.get(k) == "SELL"}

        buy_set, sell_set = self._consensus_rule(s1_buys, s2_buys, s1_sells, s2_sells)

        # Remove conflicts
        conflicts = buy_set & sell_set
        buy_set -= conflicts
        sell_set -= conflicts

        # Macro overlay
        if macro_regime == "DEFENSIVE":
            buy_set = set()
            logger.info("[ConsensusAgent] DEFENSIVE regime — clearing all buys")
        elif macro_regime == "REDUCE":
            # Keep only strongest half
            buy_set = self._top_n(buy_set, s1_strengths, s2_scores, max(1, len(buy_set) // 2))
            logger.info("[ConsensusAgent] REDUCE regime — trimmed buys to %d", len(buy_set))

        # Select top TARGET_PORTFOLIO_SIZE by combined strength
        selected = self._top_n(buy_set, s1_strengths, s2_scores, TARGET_PORTFOLIO_SIZE)
        memory_store("consensus_buys", list(selected))
        memory_store("consensus_sells", list(sell_set - selected))

        # Combined strength for ranking
        combined = {
            cid: (s1_strengths.get(cid, 0.5) + abs(s2_scores.get(cid, 0.0))) / 2
            for cid in selected
        }
        memory_store("consensus_strengths", combined)

        logger.info(
            "[ConsensusAgent] %d buys selected, %d sells, regime=%s",
            len(selected), len(sell_set), macro_regime,
        )

    # ── Consensus rule ────────────────────────────────────────────────────────

    @staticmethod
    def _consensus_rule(
        s1_buys: Set[str],
        s2_buys: Set[str],
        s1_sells: Set[str],
        s2_sells: Set[str],
    ) -> Tuple[Set[str], Set[str]]:
        """
        Intersection if >1 asset in common, else union.
        Conflict removal is done by the caller.
        """
        buy_intersection = s1_buys & s2_buys
        sell_intersection = s1_sells & s2_sells

        buy_set  = buy_intersection  if len(buy_intersection)  > 1 else (s1_buys | s2_buys)
        sell_set = sell_intersection if len(sell_intersection) > 1 else (s1_sells | s2_sells)

        return buy_set, sell_set

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _top_n(
        self,
        candidates: Set[str],
        s1_strengths: Dict[str, float],
        s2_scores: Dict[str, float],
        n: int,
    ) -> Set[str]:
        scored = []
        for cid in candidates:
            combined = (s1_strengths.get(cid, 0.5) + abs(s2_scores.get(cid, 0.0))) / 2
            scored.append((cid, combined))
        scored.sort(key=lambda x: x[1], reverse=True)
        return {cid for cid, _ in scored[:n]}
