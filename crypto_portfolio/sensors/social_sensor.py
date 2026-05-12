"""
SOCIAL SENSOR — Polls every 15 minutes.
Monitors Twitter volume spikes, viral negative narratives, Reddit activity,
and Google Trends surges.
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

import requests

from config import (
    SOCIAL_SENSOR_INTERVAL_MINUTES,
    TWEET_VOLUME_SPIKE_MULTIPLIER,
    SENTIMENT_PANIC_THRESHOLD,
    SOCIAL_PANIC_TRIGGER,
)
from models.cryptobert import CryptoBERT
from memory.claude_flow_store import memory_store, memory_retrieve

logger = logging.getLogger(__name__)

PANIC_KEYWORDS = [
    "rug pull", "exit scam", "hack", "exploit", "ponzi",
    "sec charges", "exchange down", "insolvent", "bankrupt",
]

BEARISH_TRENDS = ["crypto crash", "bitcoin dead", "sell bitcoin", "crypto collapse"]
BULLISH_TRENDS = ["buy bitcoin", "crypto bull", "bitcoin moon", "crypto rally"]


class SocialSensor:
    def __init__(self, env: dict):
        self.twitter_token = env.get("TWITTER_BEARER_TOKEN", "")
        self.reddit_id = env.get("REDDIT_CLIENT_ID", "")
        self.reddit_secret = env.get("REDDIT_CLIENT_SECRET", "")
        self.model = CryptoBERT()
        self._interval = SOCIAL_SENSOR_INTERVAL_MINUTES * 60

    def start(self, risk_evaluator_callback):
        logger.info("[SocialSensor] Starting (interval=%dm)", SOCIAL_SENSOR_INTERVAL_MINUTES)
        while True:
            try:
                panic_score, fomo_score, details = self.poll()
                memory_store("social_panic_score", panic_score)
                memory_store("social_fomo_score", fomo_score)
                memory_store("social_sensor_details", details)
                if panic_score > SOCIAL_PANIC_TRIGGER:
                    logger.warning("[SocialSensor] PANIC alert: score=%.3f", panic_score)
                    risk_evaluator_callback("social", -panic_score, details)
            except Exception as e:
                logger.error("[SocialSensor] Poll error: %s", e)
            time.sleep(self._interval)

    def poll(self) -> Tuple[float, float, Dict]:
        panic = 0.0
        fomo = 0.0
        details: Dict = {}

        panic_twitter, fomo_twitter, twitter_detail = self._check_twitter()
        panic += panic_twitter * 0.5
        fomo += fomo_twitter * 0.5
        details["twitter"] = twitter_detail

        panic_reddit, reddit_detail = self._check_reddit()
        panic += panic_reddit * 0.3
        details["reddit"] = reddit_detail

        trends_panic, trends_fomo, trends_detail = self._check_trends()
        panic += trends_panic * 0.2
        fomo += trends_fomo * 0.2
        details["trends"] = trends_detail

        return min(1.0, panic), min(1.0, fomo), details

    # ── Twitter ──────────────────────────────────────────────────────────────

    def _check_twitter(self) -> Tuple[float, float, Dict]:
        if not self.twitter_token:
            return 0.0, 0.0, {"note": "No Twitter token"}

        headers = {"Authorization": f"Bearer {self.twitter_token}"}

        # Check for panic keywords
        panic_query = " OR ".join(f'"{kw}"' for kw in PANIC_KEYWORDS[:5]) + " lang:en"
        try:
            resp = requests.get(
                "https://api.twitter.com/2/tweets/search/recent",
                headers=headers,
                params={"query": panic_query, "max_results": 100, "tweet.fields": "text"},
                timeout=15,
            )
            if resp.status_code == 200:
                tweets = resp.json().get("data", [])
                if tweets:
                    texts = [t["text"] for t in tweets]
                    avg_sentiment = sum(self.model.score(t) for t in texts[:50]) / min(50, len(texts))
                    panic_score = max(0.0, -avg_sentiment) if avg_sentiment < SENTIMENT_PANIC_THRESHOLD else 0.0
                    fomo_score = max(0.0, avg_sentiment) if avg_sentiment > 0.3 else 0.0
                    return panic_score, fomo_score, {
                        "tweet_count": len(tweets),
                        "avg_sentiment": round(avg_sentiment, 4),
                    }
        except Exception as e:
            logger.debug("Twitter social check failed: %s", e)

        return 0.0, 0.0, {}

    # ── Reddit ───────────────────────────────────────────────────────────────

    def _check_reddit(self) -> Tuple[float, Dict]:
        if not (self.reddit_id and self.reddit_secret):
            return 0.0, {"note": "No Reddit credentials"}

        try:
            auth = requests.auth.HTTPBasicAuth(self.reddit_id, self.reddit_secret)
            token_resp = requests.post(
                "https://www.reddit.com/api/v1/access_token",
                auth=auth,
                data={"grant_type": "client_credentials"},
                headers={"User-Agent": "crypto-portfolio-bot/1.0"},
                timeout=10,
            )
            token = token_resp.json().get("access_token", "")
            if not token:
                return 0.0, {}

            headers = {
                "Authorization": f"bearer {token}",
                "User-Agent": "crypto-portfolio-bot/1.0",
            }
            resp = requests.get(
                "https://oauth.reddit.com/r/CryptoCurrency/hot",
                headers=headers,
                params={"limit": 25},
                timeout=10,
            )
            if resp.status_code == 200:
                posts = resp.json().get("data", {}).get("children", [])
                texts = [p["data"]["title"] for p in posts]
                sentiments = [self.model.score(t) for t in texts]
                avg = sum(sentiments) / len(sentiments) if sentiments else 0.0
                panic = max(0.0, -avg)
                return panic, {"post_count": len(posts), "avg_sentiment": round(avg, 4)}
        except Exception as e:
            logger.debug("Reddit social check failed: %s", e)

        return 0.0, {}

    # ── Google Trends (via pytrends if available) ────────────────────────────

    def _check_trends(self) -> Tuple[float, float, Dict]:
        try:
            from pytrends.request import TrendReq
            pytrends = TrendReq(hl="en-US", tz=0)

            # Check bearish queries
            pytrends.build_payload(BEARISH_TRENDS[:2], timeframe="now 1-d")
            bearish_df = pytrends.interest_over_time()
            bearish_avg = float(bearish_df[BEARISH_TRENDS[:2]].mean().mean()) if not bearish_df.empty else 0

            pytrends.build_payload(BULLISH_TRENDS[:2], timeframe="now 1-d")
            bullish_df = pytrends.interest_over_time()
            bullish_avg = float(bullish_df[BULLISH_TRENDS[:2]].mean().mean()) if not bullish_df.empty else 0

            panic = min(1.0, bearish_avg / 100.0)
            fomo = min(1.0, bullish_avg / 100.0)
            return panic, fomo, {"bearish_trend": bearish_avg, "bullish_trend": bullish_avg}
        except ImportError:
            return 0.0, 0.0, {"note": "pytrends not installed"}
        except Exception as e:
            logger.debug("Trends check failed: %s", e)
            return 0.0, 0.0, {}
