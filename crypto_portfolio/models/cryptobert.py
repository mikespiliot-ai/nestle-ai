"""
CryptoBERT sentiment model wrapper.
Uses ElKulako/cryptobert from HuggingFace.
Falls back to a simple keyword-based scorer if the model is unavailable.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class CryptoBERT:
    """
    Wraps ElKulako/cryptobert for per-document sentiment scoring.
    Score = positive_prob - negative_prob ∈ [-1, +1].
    """

    def __init__(self):
        self._pipeline = None
        self._load_model()

    def _load_model(self):
        try:
            from transformers import pipeline
            self._pipeline = pipeline(
                "text-classification",
                model="ElKulako/cryptobert",
                tokenizer="ElKulako/cryptobert",
                return_all_scores=True,
                device=-1,  # CPU
            )
            logger.info("CryptoBERT model loaded")
        except Exception as e:
            logger.warning("CryptoBERT unavailable (%s) — using keyword fallback", e)
            self._pipeline = None

    def score(self, text: str) -> float:
        """
        Return sentiment score in [-1, +1].
        Positive = bullish, Negative = bearish.
        """
        if not text or not text.strip():
            return 0.0

        if self._pipeline is not None:
            return self._score_with_model(text)
        return self._score_keyword_fallback(text)

    def _score_with_model(self, text: str) -> float:
        try:
            truncated = text[:512]
            results = self._pipeline(truncated)
            scores = {r["label"].upper(): r["score"] for r in results[0]}
            pos = scores.get("BULLISH", scores.get("POSITIVE", scores.get("LABEL_2", 0.0)))
            neg = scores.get("BEARISH", scores.get("NEGATIVE", scores.get("LABEL_0", 0.0)))
            return float(pos - neg)
        except Exception as e:
            logger.debug("CryptoBERT inference failed: %s", e)
            return 0.0

    def _score_keyword_fallback(self, text: str) -> float:
        """Simple keyword scoring as fallback when model is unavailable."""
        text_lower = text.lower()
        positive = [
            "bull", "bullish", "moon", "pump", "surge", "rally", "gain",
            "breakout", "buy", "accumulate", "adoption", "partnership",
            "upgrade", "launch", "milestone",
        ]
        negative = [
            "bear", "bearish", "crash", "dump", "plunge", "sell", "scam",
            "hack", "exploit", "ban", "regulation", "lawsuit", "fraud",
            "insolvent", "bankrupt", "rug pull", "depeg",
        ]
        pos_count = sum(1 for w in positive if w in text_lower)
        neg_count = sum(1 for w in negative if w in text_lower)
        total = pos_count + neg_count
        if total == 0:
            return 0.0
        return (pos_count - neg_count) / total
