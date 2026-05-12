"""
BACKTEST AGENT — Paper Trading Executor + Performance Tracker
Executes rebalancing, tracks portfolio state, computes performance metrics.
"""

import json
import logging
import os
from datetime import datetime
from typing import Dict, List, Optional

from config import (
    REBALANCE_DRIFT_THRESHOLD,
    TRANSACTION_COST_RATE,
    INITIAL_CAPITAL_USD,
    PAPER_TRADING_DB,
    REPORTS_DIR,
    RISK_FREE_RATE,
)
from paper_trading.portfolio import Portfolio
from paper_trading.executor import PaperExecutor
from paper_trading.performance import PerformanceTracker
from memory.claude_flow_store import memory_store, memory_retrieve
from data.live import get_current_prices

logger = logging.getLogger(__name__)


class BacktestAgent:
    def __init__(self):
        self.portfolio = Portfolio(db_path=PAPER_TRADING_DB)
        self.executor = PaperExecutor(self.portfolio)
        self.perf = PerformanceTracker(self.portfolio)
        os.makedirs(REPORTS_DIR, exist_ok=True)

    # ── public entry point ──────────────────────────────────────────────────

    def run(self, env: dict):
        logger.info("[BacktestAgent] Monthly rebalancing")

        optimal_weights: Dict[str, float] = memory_retrieve("optimal_weights", {})
        universe_list: List[Dict] = memory_retrieve("universe_list", [])

        if not optimal_weights:
            logger.error("[BacktestAgent] No optimal_weights — aborting")
            return

        sym_to_id = {c["symbol"]: c["id"] for c in universe_list}
        cg_key = env.get("COINGECKO_API_KEY", "")
        coin_ids = list({sym_to_id.get(s, s) for s in optimal_weights})
        prices = get_current_prices(coin_ids, api_key=cg_key)
        id_to_price = prices

        # Map symbol weights → coin_id weights, get current prices
        target_weights = {}
        price_map: Dict[str, float] = {}
        for sym, w in optimal_weights.items():
            cid = sym_to_id.get(sym, sym)
            price = id_to_price.get(cid, 0.0)
            if price > 0:
                target_weights[sym] = w
                price_map[sym] = price

        # Check drift
        current_weights = self.portfolio.get_current_weights(price_map)
        drift = self._compute_drift(current_weights, target_weights)
        logger.info("[BacktestAgent] Portfolio drift=%.4f", drift)

        if drift > REBALANCE_DRIFT_THRESHOLD or not current_weights:
            self.executor.rebalance(target_weights, price_map)
            logger.info("[BacktestAgent] Rebalanced to %d positions", len(target_weights))
        else:
            logger.info("[BacktestAgent] Drift below threshold — no rebalancing needed")

        # Update NAV history
        nav = self.portfolio.compute_nav(price_map)
        self.portfolio.record_nav(nav)
        memory_store("portfolio_state", self.portfolio.get_state())

        # Compute performance metrics
        metrics = self.perf.compute_metrics()
        logger.info("[BacktestAgent] Metrics: %s", json.dumps(metrics, indent=2))

        # Generate report
        self._generate_report(metrics, target_weights, price_map)

    def run_emergency_action(self, action: str, price_map: Dict[str, float]):
        """
        Execute emergency portfolio action.
        action: 'DEFENSIVE' | 'REDUCE' | 'HEDGE'
        """
        if action == "DEFENSIVE":
            self.executor.move_to_cash(fraction=0.80, price_map=price_map)
        elif action == "REDUCE":
            self.executor.reduce_all_positions(fraction=0.40, price_map=price_map)
        elif action == "HEDGE":
            self.executor.reduce_high_beta(fraction=0.30, price_map=price_map)

        nav = self.portfolio.compute_nav(price_map)
        self.portfolio.record_nav(nav)
        memory_store("portfolio_state", self.portfolio.get_state())

    # ── helpers ─────────────────────────────────────────────────────────────

    @staticmethod
    def _compute_drift(current: Dict[str, float], target: Dict[str, float]) -> float:
        all_syms = set(current) | set(target)
        drift = sum(abs(target.get(s, 0) - current.get(s, 0)) for s in all_syms)
        return drift

    def _generate_report(self, metrics: Dict, weights: Dict, prices: Dict):
        now = datetime.utcnow()
        tag = now.strftime("%Y_%m")
        report = {
            "generated_at": now.isoformat(),
            "metrics": metrics,
            "weights": weights,
            "prices": prices,
            "best_method": memory_retrieve("best_method", ""),
            "all_sharpe_ratios": memory_retrieve("all_sharpe_ratios", {}),
        }
        path_json = os.path.join(REPORTS_DIR, f"report_{tag}.json")
        with open(path_json, "w") as f:
            json.dump(report, f, indent=2, default=str)
        logger.info("[BacktestAgent] Report saved: %s", path_json)
