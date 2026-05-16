"""BacktestAgent — drift check, rebalancing, NAV recording, performance reporting."""

import logging
import os
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional

from config import (
    DEFENSIVE_CASH_FRACTION,
    INITIAL_CAPITAL_USD,
    PAPER_TRADING_DB,
    REBALANCE_DRIFT_THRESHOLD,
    REDUCE_POSITION_FRACTION,
    REPORTS_DIR,
)
from memory.claude_flow_store import memory_retrieve, memory_store
from paper_trading.portfolio import Portfolio
from paper_trading.executor import PaperExecutor
from paper_trading.performance import PerformanceTracker

logger = logging.getLogger(__name__)


class BacktestAgent:
    """Manages the paper-trading loop and emergency actions."""

    def __init__(self, env: Optional[Dict[str, Any]] = None):
        self.env = env or {}
        self._portfolio: Optional[Portfolio] = None
        self._executor: Optional[PaperExecutor] = None
        self._testnet_executor = None
        self._init_backend()

    def _init_backend(self) -> None:
        """Auto-detect Binance testnet keys; fall back to paper executor."""
        api_key = self.env.get("BINANCE_TESTNET_API_KEY") or os.environ.get("BINANCE_TESTNET_API_KEY")
        secret = self.env.get("BINANCE_TESTNET_SECRET") or os.environ.get("BINANCE_TESTNET_SECRET")

        db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", PAPER_TRADING_DB)
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._portfolio = Portfolio(db_path)
        self._executor = PaperExecutor(self._portfolio)

        if api_key and secret:
            try:
                from paper_trading.binance_testnet import BinanceTestnetClient
                from paper_trading.testnet_executor import TestnetExecutor
                client = BinanceTestnetClient(api_key, secret)
                if client.ping():
                    self._testnet_executor = TestnetExecutor(client, self._portfolio)
                    logger.info("[BacktestAgent] Using Binance Testnet executor")
                else:
                    logger.warning("[BacktestAgent] Testnet ping failed; using PaperExecutor")
            except Exception as exc:
                logger.warning("[BacktestAgent] Testnet init error (%s); using PaperExecutor", exc)
        else:
            logger.info("[BacktestAgent] Using PaperExecutor (no testnet keys)")

    # ── Public entry point ────────────────────────────────────────────────────

    def run(self, env: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if env:
            self.env.update(env)

        logger.info("[BacktestAgent] Running backtest/rebalance cycle…")

        optimal_weights: Dict[str, float] = memory_retrieve("optimal_weights", {})
        universe = memory_retrieve("universe", [])

        # Build price map
        price_map = {c["id"]: c.get("current_price", 1.0) for c in universe}
        price_map = {k: v for k, v in price_map.items() if v and v > 0}

        # Drift check
        should_rebalance = self._check_drift(optimal_weights, price_map)
        if should_rebalance and optimal_weights:
            self._rebalance(optimal_weights, price_map)
        else:
            logger.info("[BacktestAgent] No rebalance needed (within drift threshold)")

        # Record NAV
        nav = self._portfolio.compute_nav(price_map)
        self._portfolio.record_nav(nav)
        memory_store("current_nav", nav)

        # Compute metrics
        tracker = PerformanceTracker(self._portfolio)
        metrics = tracker.compute_metrics()
        memory_store("performance_metrics", metrics)

        # Generate report
        report = self._generate_report(metrics, optimal_weights)
        memory_store("last_report", report)

        logger.info("[BacktestAgent] NAV=%.2f  Sharpe=%.3f", nav, metrics.get("sharpe_ratio", 0))
        return metrics

    def run_emergency_action(
        self, action: str, price_map: Dict[str, float]
    ) -> None:
        """Execute emergency risk actions."""
        logger.warning("[BacktestAgent] Emergency action: %s", action)
        executor = self._testnet_executor or self._executor

        if action == "DEFENSIVE":
            executor.move_to_cash(DEFENSIVE_CASH_FRACTION, price_map)
            self._portfolio.set_mode("DEFENSIVE")
        elif action == "REDUCE":
            executor.reduce_all_positions(REDUCE_POSITION_FRACTION, price_map)
            self._portfolio.set_mode("REDUCED")
        elif action == "HEDGE":
            executor.reduce_high_beta(REDUCE_POSITION_FRACTION, price_map)
            self._portfolio.set_mode("HEDGED")

        nav = self._portfolio.compute_nav(price_map)
        self._portfolio.record_nav(nav)
        memory_store("portfolio_mode", action)

    # ── Internals ─────────────────────────────────────────────────────────────

    def _check_drift(
        self, target: Dict[str, float], price_map: Dict[str, float]
    ) -> bool:
        if not target:
            return False
        current_w = self._portfolio.get_current_weights(price_map)
        for cid, tw in target.items():
            cw = current_w.get(cid, 0.0)
            if abs(tw - cw) > REBALANCE_DRIFT_THRESHOLD:
                return True
        return False

    def _rebalance(
        self, target_weights: Dict[str, float], price_map: Dict[str, float]
    ) -> None:
        executor = self._testnet_executor or self._executor
        if self._testnet_executor:
            self._testnet_executor.rebalance(target_weights)
        else:
            executor.rebalance(target_weights, price_map)

    def _generate_report(
        self, metrics: Dict[str, Any], weights: Dict[str, float]
    ) -> Dict[str, Any]:
        ts = datetime.now(timezone.utc).isoformat()
        report = {
            "timestamp": ts,
            "metrics": metrics,
            "weights": weights,
            "best_method": memory_retrieve("best_method", "N/A"),
            "sharpe_rankings": memory_retrieve("all_sharpe_ratios", {}),
        }
        os.makedirs(REPORTS_DIR, exist_ok=True)
        import json
        path = os.path.join(REPORTS_DIR, f"report_{ts[:10]}.json")
        try:
            with open(path, "w") as fh:
                json.dump(report, fh, indent=2, default=str)
        except Exception as exc:
            logger.warning("Report write error: %s", exc)
        return report
