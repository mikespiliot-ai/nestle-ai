"""
SENTIMENT AGENT — Layer 1, Agent 2
CryptoBERT-based sentiment screening (paper Section 5.1).
Sources: Twitter/X, Reddit, NewsAPI, RSS feeds.
Exponential decay weighting with 7-day half-life.
"""

import logging
import math
import os
from datetime import datetime, timedelta
from typing import Dict, List, Set, Tuple

import requests

from config import (
    SENTIMENT_BUY_THRESHOLD,
    SENTIMENT_SELL_THRESHOLD,
    SENTIMENT_HALFLIFE_DAYS,
    NEWSAPI_BASE_URL,
)
from models.cryptobert import CryptoBERT
from memory.claude_flow_store import memory_store, memory_retrieve

logger = logging.getLogger(__name__)

LAMBDA = math.log(2) / SENTIMENT_HALFLIFE_DAYS


class SentimentAgent:
    def __init__(self, env: dict):
        self.twitter_token = env.get("TWITTER_BEARER_TOKEN", "")
        self.reddit_client_id = env.get("REDDIT_CLIENT_ID", "")
        self.reddit_secret = env.get("REDDIT_CLIENT_SECRET", "")
        self.newsapi_key = env.get("NEWSAPI_KEY", "")
        self.model = CryptoBERT()

    # ── public entry point ──────────────────────────────────────────────────

    def run(self):
        logger.info("[SentimentAgent] Starting sentiment screening")

        universe: List[Dict] = memory_retrieve("universe_list", [])
        if not universe:
            logger.error("[SentimentAgent] No universe in memory — aborting")
            return

        buys: Set[str] = set()
        sells: Set[str] = set()
        scores: Dict[str, float] = {}

        for coin in universe:
            symbol = coin["symbol"]
            name = coin["name"]
            score = self._compute_weighted_sentiment(symbol, name)
            scores[symbol] = round(score, 4)

            if score > SENTIMENT_BUY_THRESHOLD:
                buys.add(symbol)
            elif score < SENTIMENT_SELL_THRESHOLD:
                sells.add(symbol)

        logger.info("[SentimentAgent] Buys=%d  Sells=%d", len(buys), len(sells))
        memory_store("s2_signals", {"buys": list(buys), "sells": list(sells)})
        memory_store("s2_scores", scores)

    # ── sentiment computation ───────────────────────────────────────────────

    def _compute_weighted_sentiment(self, symbol: str, name: str) -> float:
        docs: List[Tuple[str, int]] = []  # (text, days_ago)

        docs.extend(self._fetch_twitter(symbol, name))
        docs.extend(self._fetch_reddit(symbol, name))
        docs.extend(self._fetch_news(symbol, name))

        if not docs:
            return 0.0

        weighted_sum = 0.0
        weight_sum = 0.0

        for text, days_ago in docs:
            score = self.model.score(text)
            w = math.exp(-LAMBDA * max(0, days_ago))
            weighted_sum += w * score
            weight_sum += w

        return weighted_sum / weight_sum if weight_sum > 0 else 0.0

    # ── data sources ────────────────────────────────────────────────────────

    def _fetch_twitter(self, symbol: str, name: str) -> List[Tuple[str, int]]:
        if not self.twitter_token:
            return []
        query = f"${symbol} OR {name} lang:en -is:retweet"
        url = "https://api.twitter.com/2/tweets/search/recent"
        headers = {"Authorization": f"Bearer {self.twitter_token}"}
        params = {
            "query": query,
            "max_results": 100,
            "tweet.fields": "created_at",
        }
        try:
            resp = requests.get(url, headers=headers, params=params, timeout=15)
            if resp.status_code == 429:
                logger.warning("Twitter rate limit hit")
                return []
            resp.raise_for_status()
            tweets = resp.json().get("data", [])
            now = datetime.utcnow()
            results = []
            for t in tweets:
                created = datetime.fromisoformat(t["created_at"].replace("Z", ""))
                days_ago = (now - created).days
                results.append((t["text"], days_ago))
            return results
        except Exception as e:
            logger.debug("Twitter fetch failed for %s: %s", symbol, e)
            return []

    def _fetch_reddit(self, symbol: str, name: str) -> List[Tuple[str, int]]:
        if not (self.reddit_client_id and self.reddit_secret):
            return []
        auth = requests.auth.HTTPBasicAuth(self.reddit_client_id, self.reddit_secret)
        headers = {"User-Agent": "crypto-portfolio-bot/1.0"}
        try:
            token_resp = requests.post(
                "https://www.reddit.com/api/v1/access_token",
                auth=auth,
                data={"grant_type": "client_credentials"},
                headers=headers,
                timeout=10,
            )
            token = token_resp.json().get("access_token", "")
            if not token:
                return []
        except Exception:
            return []

        headers["Authorization"] = f"bearer {token}"
        subreddits = ["CryptoCurrency", "Bitcoin", "ethereum", symbol.lower()]
        docs = []
        now = datetime.utcnow()

        for sub in subreddits:
            try:
                url = f"https://oauth.reddit.com/r/{sub}/search"
                params = {"q": name, "sort": "new", "limit": 25, "t": "month"}
                resp = requests.get(url, headers=headers, params=params, timeout=10)
                if resp.status_code != 200:
                    continue
                posts = resp.json().get("data", {}).get("children", [])
                for p in posts:
                    data = p["data"]
                    created = datetime.utcfromtimestamp(data.get("created_utc", 0))
                    days_ago = (now - created).days
                    text = data.get("title", "") + " " + data.get("selftext", "")
                    docs.append((text[:512], days_ago))
            except Exception as e:
                logger.debug("Reddit fetch failed for %s/%s: %s", sub, symbol, e)

        return docs

    def _fetch_news(self, symbol: str, name: str) -> List[Tuple[str, int]]:
        if not self.newsapi_key:
            return []
        url = f"{NEWSAPI_BASE_URL}/everything"
        params = {
            "q": f"{name} OR {symbol} crypto",
            "apiKey": self.newsapi_key,
            "language": "en",
            "sortBy": "publishedAt",
            "pageSize": 50,
            "from": (datetime.utcnow() - timedelta(days=30)).strftime("%Y-%m-%d"),
        }
        try:
            resp = requests.get(url, params=params, timeout=15)
            resp.raise_for_status()
            articles = resp.json().get("articles", [])
            now = datetime.utcnow()
            results = []
            for a in articles:
                pub = a.get("publishedAt", "")
                try:
                    dt = datetime.fromisoformat(pub.replace("Z", ""))
                    days_ago = (now - dt).days
                except Exception:
                    days_ago = 15
                text = (a.get("title") or "") + " " + (a.get("description") or "")
                results.append((text[:512], days_ago))
            return results
        except Exception as e:
            logger.debug("NewsAPI fetch failed for %s: %s", symbol, e)
            return []
