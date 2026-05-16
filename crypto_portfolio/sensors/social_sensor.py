"""SocialSensor — monitors Twitter, Reddit, Google Trends for panic/FOMO signals."""

import logging
import threading
import time
from typing import Any, Callable, Dict, Optional, Tuple

from config import (
    SENTIMENT_PANIC_THRESHOLD,
    SOCIAL_FOMO_TRIGGER,
    SOCIAL_PANIC_TRIGGER,
    SOCIAL_SENSOR_INTERVAL_MINUTES,
    TWEET_VOLUME_SPIKE_MULTIPLIER,
)
from models.cryptobert import CryptoBERT

logger = logging.getLogger(__name__)

_PANIC_KEYWORDS = {
    "crash", "dump", "rekt", "scam", "hack", "rug", "panic", "sell",
    "capitulation", "bear", "collapse", "bankrupt", "fraud", "shutdown",
    "liquidation", "contagion", "depeg",
}
_FOMO_KEYWORDS = {
    "moon", "ath", "pump", "bull", "buy", "lambo", "10x", "rally",
    "breakout", "accumulate", "hodl", "institutional", "etf",
}


class SocialSensor:
    """Polls social media for panic and FOMO signals."""

    def __init__(self, env: Dict[str, Any], risk_evaluator_callback: Optional[Callable] = None):
        self.env = env
        self._callback = risk_evaluator_callback
        self._bert = CryptoBERT()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._prev_tweet_volume: Optional[int] = None

    def start(self) -> None:
        self._running = True
        self._thread = threading.Thread(target=self._poll_loop, daemon=True, name="SocialSensor")
        self._thread.start()
        logger.info("[SocialSensor] Started (interval=%dm)", SOCIAL_SENSOR_INTERVAL_MINUTES)

    def stop(self) -> None:
        self._running = False

    def _poll_loop(self) -> None:
        while self._running:
            try:
                panic_score, fomo_score, details = self.scan()
                if panic_score > SOCIAL_PANIC_TRIGGER and self._callback:
                    self._callback("social_panic", panic_score, details)
                elif fomo_score > SOCIAL_FOMO_TRIGGER and self._callback:
                    self._callback("social_fomo", fomo_score, details)
            except Exception as exc:
                logger.error("[SocialSensor] Poll error: %s", exc)
            time.sleep(SOCIAL_SENSOR_INTERVAL_MINUTES * 60)

    def scan(self) -> Tuple[float, float, Dict]:
        """Return (panic_score, fomo_score, details) each in [0, 1]."""
        details: Dict[str, Any] = {}

        twitter_panic, twitter_fomo = self._scan_twitter(details)
        reddit_panic, reddit_fomo = self._scan_reddit(details)
        trends_panic = self._scan_google_trends(details)

        panic = (twitter_panic * 0.5 + reddit_panic * 0.3 + trends_panic * 0.2)
        fomo  = (twitter_fomo  * 0.5 + reddit_fomo  * 0.5)

        panic = max(0.0, min(1.0, panic))
        fomo  = max(0.0, min(1.0, fomo))

        logger.debug("[SocialSensor] panic=%.3f fomo=%.3f", panic, fomo)
        return panic, fomo, details

    # ── Twitter ───────────────────────────────────────────────────────────────

    def _scan_twitter(self, details: Dict) -> Tuple[float, float]:
        try:
            import tweepy
            bearer = self.env.get("TWITTER_BEARER_TOKEN")
            if not bearer:
                return 0.0, 0.0
            client = tweepy.Client(bearer_token=bearer, wait_on_rate_limit=False)
            resp = client.search_recent_tweets(
                query="crypto OR bitcoin OR ethereum -is:retweet lang:en",
                max_results=50,
                tweet_fields=["text"],
            )
            if not resp.data:
                return 0.0, 0.0

            tweets = [t.text for t in resp.data]
            volume = len(tweets)
            details["tweet_volume"] = volume

            # Volume spike check
            volume_panic = 0.0
            if self._prev_tweet_volume and volume > self._prev_tweet_volume * TWEET_VOLUME_SPIKE_MULTIPLIER:
                volume_panic = min(1.0, volume / (self._prev_tweet_volume * TWEET_VOLUME_SPIKE_MULTIPLIER))
            self._prev_tweet_volume = volume

            # Keyword + sentiment scoring
            panic_count = sum(1 for t in tweets if any(kw in t.lower() for kw in _PANIC_KEYWORDS))
            fomo_count  = sum(1 for t in tweets if any(kw in t.lower() for kw in _FOMO_KEYWORDS))

            avg_sentiment = sum(self._bert.score(t) for t in tweets[:20]) / min(20, len(tweets))
            sentiment_panic = max(0.0, -avg_sentiment) if avg_sentiment < SENTIMENT_PANIC_THRESHOLD else 0.0

            panic = max(volume_panic, panic_count / volume, sentiment_panic)
            fomo  = fomo_count / volume
            details["twitter_panic"] = panic
            return panic, fomo
        except Exception as exc:
            logger.debug("Twitter scan error: %s", exc)
            return 0.0, 0.0

    # ── Reddit ────────────────────────────────────────────────────────────────

    def _scan_reddit(self, details: Dict) -> Tuple[float, float]:
        try:
            import praw
            cid = self.env.get("REDDIT_CLIENT_ID")
            cs  = self.env.get("REDDIT_CLIENT_SECRET")
            if not cid or not cs:
                return 0.0, 0.0
            reddit = praw.Reddit(
                client_id=cid,
                client_secret=cs,
                user_agent="crypto_portfolio_sensor/1.0",
            )
            posts = list(reddit.subreddit("CryptoCurrency").hot(limit=25))
            if not posts:
                return 0.0, 0.0

            texts = [p.title + " " + (p.selftext or "") for p in posts]
            panic_count = sum(1 for t in texts if any(kw in t.lower() for kw in _PANIC_KEYWORDS))
            fomo_count  = sum(1 for t in texts if any(kw in t.lower() for kw in _FOMO_KEYWORDS))
            n = len(texts)
            details["reddit_panic"] = panic_count / n
            return panic_count / n, fomo_count / n
        except Exception as exc:
            logger.debug("Reddit scan error: %s", exc)
            return 0.0, 0.0

    # ── Google Trends ─────────────────────────────────────────────────────────

    def _scan_google_trends(self, details: Dict) -> float:
        try:
            from pytrends.request import TrendReq
            pytrends = TrendReq(hl="en-US", tz=0, timeout=(5, 20))
            pytrends.build_payload(["bitcoin crash", "crypto sell"], timeframe="now 1-d")
            data = pytrends.interest_over_time()
            if not data.empty:
                avg = float(data[["bitcoin crash", "crypto sell"]].mean().mean())
                score = avg / 100.0
                details["google_trends_panic"] = score
                return score
        except Exception as exc:
            logger.debug("Google Trends error: %s", exc)
        return 0.0
