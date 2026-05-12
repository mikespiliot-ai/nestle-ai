"""
MACRO SENSOR — Polls every 60 minutes.
Monitors Fed/ECB announcements, CPI/PPI releases, regulatory news,
geopolitical events, and exchange/stablecoin crises.
"""

import logging
import time
from datetime import datetime
from typing import Dict, List

import requests

from config import (
    MACRO_SENSOR_INTERVAL_MINUTES,
    NEWSAPI_BASE_URL,
    MACRO_EVENT_WEIGHTS,
)
from memory.claude_flow_store import memory_store, memory_retrieve

logger = logging.getLogger(__name__)


class MacroSensor:
    def __init__(self, env: dict):
        self.newsapi_key = env.get("NEWSAPI_KEY", "")
        self.fred_key = env.get("FRED_API_KEY", "")
        self._interval = MACRO_SENSOR_INTERVAL_MINUTES * 60

    def start(self, risk_evaluator_callback):
        logger.info("[MacroSensor] Starting (interval=%dm)", MACRO_SENSOR_INTERVAL_MINUTES)
        while True:
            try:
                score, events = self.poll()
                memory_store("macro_sensor_score", score)
                memory_store("macro_sensor_events", events)
                if score < -0.4:
                    logger.warning("[MacroSensor] Alert: score=%.3f  events=%s", score, events)
                    risk_evaluator_callback("macro", score, events)
            except Exception as e:
                logger.error("[MacroSensor] Poll error: %s", e)
            time.sleep(self._interval)

    def poll(self) -> tuple:
        events = []
        score = 0.0

        events.extend(self._scan_news())
        for ev in events:
            score += ev.get("weight", 0.0) * ev.get("recency", 1.0)

        score = max(-1.0, min(1.0, score))
        return score, events

    # ── news scanning ────────────────────────────────────────────────────────

    def _scan_news(self) -> List[Dict]:
        if not self.newsapi_key:
            return []

        queries = {
            "exchange_hack_large": 'crypto exchange hack OR "exchange hacked" OR "funds stolen"',
            "stablecoin_depeg": '"stablecoin" AND ("depeg" OR "depegged" OR "collapse")',
            "country_bans_crypto": '"crypto ban" OR "bitcoin ban" OR "ban cryptocurrency"',
            "country_legalizes_crypto": '"legal tender" OR "crypto legal" OR "legalizes bitcoin"',
            "regulatory_clarity": '"crypto regulation" AND ("clarity" OR "approved" OR "framework")',
            "geopolitical_escalation": 'war escalation OR military conflict OR sanctions crypto',
            "fed_rate_hike_unexpected": '"federal reserve" AND ("rate hike" OR "rate increase") AND unexpected',
            "fed_rate_cut": '"federal reserve" AND "rate cut"',
        }

        found_events = []
        for event_type, query in queries.items():
            articles = self._fetch_news(query, page_size=5)
            if articles:
                recency = self._compute_recency(articles)
                weight = MACRO_EVENT_WEIGHTS.get(event_type, 0.0)
                found_events.append({
                    "type": event_type,
                    "weight": weight,
                    "recency": recency,
                    "articles": [a.get("title", "") for a in articles[:3]],
                    "detected_at": datetime.utcnow().isoformat(),
                })
        return found_events

    def _fetch_news(self, query: str, page_size: int = 10) -> List[Dict]:
        if not self.newsapi_key:
            return []
        url = f"{NEWSAPI_BASE_URL}/everything"
        params = {
            "q": query,
            "apiKey": self.newsapi_key,
            "language": "en",
            "sortBy": "publishedAt",
            "pageSize": page_size,
        }
        try:
            resp = requests.get(url, params=params, timeout=10)
            if resp.status_code == 200:
                return resp.json().get("articles", [])
        except Exception as e:
            logger.debug("NewsAPI failed: %s", e)
        return []

    def _compute_recency(self, articles: List[Dict]) -> float:
        if not articles:
            return 0.0
        latest_pub = articles[0].get("publishedAt", "")
        try:
            dt = datetime.fromisoformat(latest_pub.replace("Z", ""))
            hours_ago = (datetime.utcnow() - dt).total_seconds() / 3600
            return max(0.0, 1.0 - hours_ago / 48.0)  # Decay over 48h
        except Exception:
            return 0.5
