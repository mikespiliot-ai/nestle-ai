"""MacroSensor — polls NewsAPI for macro/regulatory events and triggers callbacks."""

import logging
import threading
import time
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

import requests

from config import (
    MACRO_EVENT_WEIGHTS,
    MACRO_REDUCE_THRESHOLD,
    MACRO_SENSOR_INTERVAL_MINUTES,
    NEWSAPI_BASE_URL,
)

logger = logging.getLogger(__name__)

_MACRO_KEYWORDS = {
    "federal reserve": "fed_rate_hike",
    "rate hike": "fed_rate_hike",
    "rate cut": "fed_rate_cut",
    "interest rate": "fed_rate_hike",
    "sec": "regulatory_ban",
    "regulation": "regulatory_ban",
    "ban": "regulatory_ban",
    "etf approved": "etf_approval",
    "etf approval": "etf_approval",
    "hack": "exchange_hack",
    "exploit": "exchange_hack",
    "recession": "macro_recession",
    "inflation": "inflation_spike",
    "liquidity": "liquidity_crisis",
    "crisis": "liquidity_crisis",
    "crash": "market_crash",
    "geopolitical": "geopolitical_crisis",
    "war": "geopolitical_crisis",
}


class MacroSensor:
    """Polls NewsAPI for macro events and invokes risk callback if score < threshold."""

    def __init__(self, env: Dict[str, Any], risk_evaluator_callback: Optional[Callable] = None):
        self.env = env
        self._callback = risk_evaluator_callback
        self._newsapi_key = env.get("NEWSAPI_KEY")
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        self._running = True
        self._thread = threading.Thread(target=self._poll_loop, daemon=True, name="MacroSensor")
        self._thread.start()
        logger.info("[MacroSensor] Started (interval=%dm)", MACRO_SENSOR_INTERVAL_MINUTES)

    def stop(self) -> None:
        self._running = False

    def _poll_loop(self) -> None:
        while self._running:
            try:
                score, details = self.scan()
                if score < MACRO_REDUCE_THRESHOLD and self._callback:
                    self._callback("macro", abs(score), details)
            except Exception as exc:
                logger.error("[MacroSensor] Poll error: %s", exc)
            time.sleep(MACRO_SENSOR_INTERVAL_MINUTES * 60)

    def scan(self):
        """Scan NewsAPI and return (score, details)."""
        articles = self._fetch_articles()
        score, details = self._score_articles(articles)
        logger.debug("[MacroSensor] score=%.3f articles=%d", score, len(articles))
        return score, details

    def _fetch_articles(self) -> List[Dict]:
        if not self._newsapi_key:
            return []
        try:
            params = {
                "q": "crypto OR bitcoin OR federal reserve OR SEC regulation",
                "apiKey": self._newsapi_key,
                "language": "en",
                "pageSize": 30,
                "sortBy": "publishedAt",
            }
            resp = requests.get(f"{NEWSAPI_BASE_URL}/everything", params=params, timeout=15)
            resp.raise_for_status()
            return resp.json().get("articles", [])
        except Exception as exc:
            logger.warning("[MacroSensor] News fetch error: %s", exc)
            return []

    def _score_articles(self, articles: List[Dict]):
        if not articles:
            return 0.0, []

        now = datetime.now(timezone.utc)
        total_score = 0.0
        total_weight = 0.0
        details = []

        for article in articles:
            text = ((article.get("title") or "") + " " + (article.get("description") or "")).lower()
            pub = article.get("publishedAt", "")
            age_hours = 0.0
            if pub:
                try:
                    t = datetime.fromisoformat(pub.replace("Z", "+00:00"))
                    age_hours = (now - t).total_seconds() / 3600
                except Exception:
                    pass

            # Detect event type
            event_type = "default"
            for keyword, etype in _MACRO_KEYWORDS.items():
                if keyword in text:
                    event_type = etype
                    break

            weight_base = MACRO_EVENT_WEIGHTS.get(event_type, MACRO_EVENT_WEIGHTS.get("default", -0.3))
            recency_weight = max(0.1, 1.0 - age_hours / 72.0)
            total_score += weight_base * recency_weight
            total_weight += recency_weight
            details.append({"event": event_type, "age_hours": age_hours, "score": weight_base})

        composite = total_score / total_weight if total_weight > 0 else 0.0
        composite = max(-1.0, min(1.0, composite))
        return composite, details
