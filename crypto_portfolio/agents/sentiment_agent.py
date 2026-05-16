"""SentimentAgent — aggregates social sentiment via CryptoBERT."""

import logging
import math
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from config import (
    SENTIMENT_BUY_THRESHOLD,
    SENTIMENT_HALFLIFE_DAYS,
    SENTIMENT_SELL_THRESHOLD,
)
from memory.claude_flow_store import memory_retrieve, memory_store
from models.cryptobert import CryptoBERT

logger = logging.getLogger(__name__)

_LAMBDA = math.log(2) / SENTIMENT_HALFLIFE_DAYS  # decay constant


class SentimentAgent:
    """Fetches text from Twitter, Reddit, NewsAPI and scores via CryptoBERT."""

    def __init__(self, env: Dict[str, Any]):
        self.env = env
        self.bert = CryptoBERT()
        self._twitter_client = None
        self._reddit_client = None
        self._newsapi_key = env.get("NEWSAPI_KEY")

    def run(self) -> None:
        logger.info("[SentimentAgent] Running sentiment analysis…")

        universe: List[Dict[str, Any]] = memory_retrieve("universe", [])
        signals: Dict[str, str] = {}
        scores: Dict[str, float] = {}

        for coin in universe:
            cid = coin["id"]
            symbol = coin.get("symbol", cid).upper()
            name = coin.get("name", symbol)

            texts = self._collect_texts(symbol, name)
            score = self._aggregate_score(texts)
            scores[cid] = score

            if score >= SENTIMENT_BUY_THRESHOLD:
                signals[cid] = "BUY"
            elif score <= SENTIMENT_SELL_THRESHOLD:
                signals[cid] = "SELL"
            else:
                signals[cid] = "NEUTRAL"

        memory_store("s2_signals", signals)
        memory_store("s2_scores", scores)
        logger.info(
            "[SentimentAgent] %d BUY, %d SELL, %d NEUTRAL",
            sum(1 for v in signals.values() if v == "BUY"),
            sum(1 for v in signals.values() if v == "SELL"),
            sum(1 for v in signals.values() if v == "NEUTRAL"),
        )

    # ── Text collection ───────────────────────────────────────────────────────

    def _collect_texts(self, symbol: str, name: str) -> List[Dict]:
        """Collect raw text items with timestamps from available sources."""
        texts = []
        now = datetime.now(timezone.utc)

        # Twitter / X
        texts.extend(self._fetch_twitter(symbol, now))

        # Reddit
        texts.extend(self._fetch_reddit(symbol, name, now))

        # NewsAPI
        texts.extend(self._fetch_news(symbol, name, now))

        return texts

    def _fetch_twitter(self, symbol: str, now: datetime) -> List[Dict]:
        results = []
        try:
            import tweepy
            bearer = self.env.get("TWITTER_BEARER_TOKEN")
            if not bearer:
                return []
            if self._twitter_client is None:
                self._twitter_client = tweepy.Client(bearer_token=bearer, wait_on_rate_limit=False)
            resp = self._twitter_client.search_recent_tweets(
                query=f"#{symbol} OR ${symbol} -is:retweet lang:en",
                max_results=20,
                tweet_fields=["created_at", "text"],
            )
            if resp.data:
                for tweet in resp.data:
                    age_hours = 0.0
                    if tweet.created_at:
                        age_hours = (now - tweet.created_at.replace(tzinfo=timezone.utc)).total_seconds() / 3600
                    results.append({"text": tweet.text, "age_hours": age_hours})
        except Exception as exc:
            logger.debug("Twitter fetch error for %s: %s", symbol, exc)
        return results

    def _fetch_reddit(self, symbol: str, name: str, now: datetime) -> List[Dict]:
        results = []
        try:
            import praw
            client_id = self.env.get("REDDIT_CLIENT_ID")
            client_secret = self.env.get("REDDIT_CLIENT_SECRET")
            if not client_id or not client_secret:
                return []
            if self._reddit_client is None:
                self._reddit_client = praw.Reddit(
                    client_id=client_id,
                    client_secret=client_secret,
                    user_agent="crypto_portfolio_bot/1.0",
                )
            subreddit = self._reddit_client.subreddit("CryptoCurrency+Bitcoin+ethereum")
            for post in subreddit.search(f"{symbol} OR {name}", limit=10, sort="new"):
                age_hours = (now.timestamp() - post.created_utc) / 3600
                results.append({"text": post.title + " " + (post.selftext or ""), "age_hours": age_hours})
        except Exception as exc:
            logger.debug("Reddit fetch error for %s: %s", symbol, exc)
        return results

    def _fetch_news(self, symbol: str, name: str, now: datetime) -> List[Dict]:
        results = []
        try:
            if not self._newsapi_key:
                return []
            import requests
            from config import NEWSAPI_BASE_URL
            params = {
                "q": f"{symbol} OR {name} crypto",
                "apiKey": self._newsapi_key,
                "language": "en",
                "pageSize": 10,
                "sortBy": "publishedAt",
            }
            resp = requests.get(f"{NEWSAPI_BASE_URL}/everything", params=params, timeout=15)
            resp.raise_for_status()
            for article in resp.json().get("articles", []):
                pub = article.get("publishedAt", "")
                age_hours = 0.0
                if pub:
                    try:
                        from datetime import datetime as dt
                        t = dt.fromisoformat(pub.replace("Z", "+00:00"))
                        age_hours = (now - t).total_seconds() / 3600
                    except Exception:
                        pass
                text = (article.get("title") or "") + " " + (article.get("description") or "")
                results.append({"text": text, "age_hours": age_hours})
        except Exception as exc:
            logger.debug("NewsAPI fetch error for %s: %s", symbol, exc)
        return results

    # ── Score aggregation ─────────────────────────────────────────────────────

    def _aggregate_score(self, texts: List[Dict]) -> float:
        """Exponential decay weighted average of CryptoBERT scores."""
        if not texts:
            return 0.0

        total_weight = 0.0
        weighted_score = 0.0

        for item in texts:
            age_days = item.get("age_hours", 0.0) / 24.0
            weight = math.exp(-_LAMBDA * age_days)
            score = self.bert.score(item.get("text", ""))
            weighted_score += weight * score
            total_weight += weight

        if total_weight < 1e-12:
            return 0.0
        return weighted_score / total_weight
