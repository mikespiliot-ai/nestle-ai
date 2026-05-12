"""
CRYPTOSIGNAL AGENT — Layer 1, Agent 1
LLM-based screening adapted from paper Section 5.1.
Classifies each asset as BUY / NEUTRAL / SELL using standardized fundamentals only.
No price levels, returns, or USD values in prompt (anti-bias per paper).
"""

import logging
import os
from typing import Dict, Set, Tuple

import anthropic

from config import FEATURES, TARGET_PORTFOLIO_SIZE
from memory.claude_flow_store import memory_store, memory_retrieve

logger = logging.getLogger(__name__)

PROMPT_TEMPLATE = """\
Given the following standardized metrics for a cryptocurrency asset:
- Size (log market cap z-score): {log_mcap_z:.3f}
- Liquidity (volume/mcap z-score): {vol_to_mcap_z:.3f}
- Momentum (30d z-score): {mom30d_z:.3f}
- Network Value vs Transactions (NVT z-score): {nvt_ratio_z:.3f}
- Volatility (realized vol z-score): {realized_vol_z:.3f}
- Category: {category}

Based purely on these fundamental characteristics and without considering \
price trends or market sentiment, classify this asset as:
BUY / NEUTRAL / SELL

Respond with only one word."""


class CryptoSignalAgent:
    def __init__(self, env: dict):
        self.client = anthropic.Anthropic(api_key=env["ANTHROPIC_API_KEY"])
        self.model = "claude-haiku-4-5-20251001"  # Fast and cheap for bulk classification

    # ── public entry point ──────────────────────────────────────────────────

    def run(self):
        logger.info("[CryptoSignalAgent] Starting LLM-S screening")

        features_matrix: Dict = memory_retrieve("features_matrix", {})
        if not features_matrix:
            logger.error("[CryptoSignalAgent] No features_matrix in memory — aborting")
            return

        buys: Set[str] = set()
        sells: Set[str] = set()
        strengths: Dict[str, float] = {}

        for symbol, feats in features_matrix.items():
            signal, confidence = self._classify_asset(symbol, feats)
            strengths[symbol] = confidence
            if signal == "BUY":
                buys.add(symbol)
            elif signal == "SELL":
                sells.add(symbol)

        logger.info("[CryptoSignalAgent] Buys=%d  Sells=%d", len(buys), len(sells))
        memory_store("s1_signals", {"buys": list(buys), "sells": list(sells)})
        memory_store("s1_strengths", strengths)

    # ── LLM classification ──────────────────────────────────────────────────

    def _classify_asset(self, symbol: str, feats: Dict) -> Tuple[str, float]:
        prompt = PROMPT_TEMPLATE.format(
            log_mcap_z=feats.get("log_mcap_z", 0.0),
            vol_to_mcap_z=feats.get("vol_to_mcap_z", 0.0),
            mom30d_z=feats.get("mom30d_z", 0.0),
            nvt_ratio_z=feats.get("nvt_ratio_z", 0.0),
            realized_vol_z=feats.get("realized_vol_z", 0.0),
            category=feats.get("category", "Unknown"),
        )

        try:
            resp = self.client.messages.create(
                model=self.model,
                max_tokens=10,
                messages=[{"role": "user", "content": prompt}],
            )
            answer = resp.content[0].text.strip().upper()
        except Exception as e:
            logger.warning("[CryptoSignalAgent] API error for %s: %s", symbol, e)
            answer = "NEUTRAL"

        signal = "NEUTRAL"
        if "BUY" in answer:
            signal = "BUY"
        elif "SELL" in answer:
            signal = "SELL"

        # Confidence proxy: distance of momentum z-score from zero
        confidence = abs(feats.get("mom30d_z", 0.0)) * 0.4 + abs(feats.get("log_mcap_z", 0.0)) * 0.3
        return signal, float(confidence)
