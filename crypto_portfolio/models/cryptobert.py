"""CryptoBERT sentiment scorer with keyword fallback."""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

_POSITIVE_KEYWORDS = {
    "bull", "moon", "pump", "surge", "rally", "buy", "adoption",
    "breakout", "bullish", "gains", "profit", "ath", "uptrend",
    "institutional", "etf", "upgrade", "partnership", "launch",
    "accumulate", "hodl", "recovery", "rebound",
}
_NEGATIVE_KEYWORDS = {
    "bear", "crash", "dump", "hack", "scam", "ban", "bearish",
    "loss", "sell", "panic", "bubble", "fraud", "exploit", "rug",
    "pullback", "correction", "fud", "liquidation", "capitulation",
    "regulation", "crackdown", "shutdown", "bankrupt", "insolvent",
}


class _KeywordScorer:
    """Simple bag-of-words fallback when transformers is unavailable."""

    def score(self, text: str) -> float:
        tokens = set(text.lower().split())
        pos = len(tokens & _POSITIVE_KEYWORDS)
        neg = len(tokens & _NEGATIVE_KEYWORDS)
        total = pos + neg
        if total == 0:
            return 0.0
        return (pos - neg) / total


class CryptoBERT:
    """Wrapper around ElKulako/cryptobert for sentiment scoring.

    *score(text)* returns a float in [-1, +1]:
      +1 = maximally bullish, -1 = maximally bearish.
    Falls back to a keyword scorer if the model cannot be loaded.
    """

    def __init__(self):
        self._pipeline: Optional[object] = None
        self._fallback = _KeywordScorer()
        self._load_model()

    def _load_model(self) -> None:
        try:
            from transformers import pipeline  # type: ignore
            self._pipeline = pipeline(
                "text-classification",
                model="ElKulako/cryptobert",
                truncation=True,
                max_length=512,
            )
            logger.info("CryptoBERT model loaded successfully.")
        except Exception as exc:
            logger.warning("CryptoBERT unavailable (%s); using keyword fallback.", exc)
            self._pipeline = None

    def score(self, text: str) -> float:
        """Return sentiment score in [-1, +1]."""
        if not text or not text.strip():
            return 0.0

        if self._pipeline is None:
            return self._fallback.score(text)

        try:
            result = self._pipeline(text[:512])[0]
            label = result.get("label", "").upper()
            confidence = float(result.get("score", 0.5))

            # CryptoBERT labels: Bullish / Bearish / Neutral
            if "BULL" in label or label in ("POSITIVE", "LABEL_2"):
                return confidence
            elif "BEAR" in label or label in ("NEGATIVE", "LABEL_0"):
                return -confidence
            else:
                return 0.0
        except Exception as exc:
            logger.error("CryptoBERT inference error: %s", exc)
            return self._fallback.score(text)
