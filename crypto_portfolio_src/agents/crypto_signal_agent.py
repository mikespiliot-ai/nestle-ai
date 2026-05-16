"""CryptoSignalAgent — uses Claude Haiku to generate BUY/NEUTRAL/SELL signals."""

import logging
import os
from typing import Any, Dict, List

import anthropic

from config import FEATURES, TARGET_PORTFOLIO_SIZE
from memory.claude_flow_store import memory_retrieve, memory_store

logger = logging.getLogger(__name__)

_MODEL = "claude-haiku-4-5-20251001"

_SYSTEM_PROMPT = (
    "You are a quantitative crypto analyst. You will be given z-scored features "
    "(standardized, no price levels) for a cryptocurrency and must output exactly "
    "one of: BUY, NEUTRAL, or SELL, followed by a confidence score between 0 and 1. "
    "Format: SIGNAL|SCORE  e.g. BUY|0.75  Do not include any other text."
)


class CryptoSignalAgent:
    """Generates trading signals per asset using Claude Haiku."""

    def __init__(self, env: Dict[str, Any]):
        self.env = env
        api_key = env.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_API_KEY", "")
        self.client = anthropic.Anthropic(api_key=api_key)

    def run(self) -> None:
        logger.info("[CryptoSignalAgent] Generating signals…")

        features: Dict[str, Dict[str, float]] = memory_retrieve("features", {})
        universe: List[Dict[str, Any]] = memory_retrieve("universe", [])

        signals: Dict[str, str] = {}
        strengths: Dict[str, float] = {}

        for coin in universe:
            cid = coin["id"]
            symbol = coin.get("symbol", cid).upper()
            feat = features.get(cid)
            if feat is None:
                continue

            prompt = self._build_prompt(symbol, feat)
            signal, strength = self._query_claude(prompt)
            signals[cid] = signal
            strengths[cid] = strength

        memory_store("s1_signals", signals)
        memory_store("s1_strengths", strengths)
        logger.info(
            "[CryptoSignalAgent] Signals: %d BUY, %d SELL, %d NEUTRAL",
            sum(1 for v in signals.values() if v == "BUY"),
            sum(1 for v in signals.values() if v == "SELL"),
            sum(1 for v in signals.values() if v == "NEUTRAL"),
        )

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _build_prompt(self, symbol: str, feat: Dict[str, float]) -> str:
        feat_lines = "\n".join(
            f"  {k}: {v:+.3f}" for k, v in feat.items() if k in FEATURES
        )
        return (
            f"Asset: {symbol}\n"
            f"Z-scored features:\n{feat_lines}\n\n"
            "Based solely on these z-scored features, output your signal."
        )

    def _query_claude(self, prompt: str):
        try:
            message = self.client.messages.create(
                model=_MODEL,
                max_tokens=20,
                system=_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )
            text = message.content[0].text.strip().upper()
            parts = text.split("|")
            signal = parts[0].strip() if parts else "NEUTRAL"
            if signal not in ("BUY", "SELL", "NEUTRAL"):
                signal = "NEUTRAL"
            strength = float(parts[1]) if len(parts) > 1 else 0.5
            strength = max(0.0, min(1.0, strength))
            return signal, strength
        except Exception as exc:
            logger.warning("Claude signal error: %s", exc)
            return "NEUTRAL", 0.0
