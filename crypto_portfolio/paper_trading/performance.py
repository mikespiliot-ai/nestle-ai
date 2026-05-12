"""
Performance metrics computation for the paper trading portfolio.
Computes Sharpe, drawdown, Calmar, win rate, and benchmark comparisons.
"""

import logging
from typing import Dict, List

import numpy as np

from config import INITIAL_CAPITAL_USD, RISK_FREE_RATE
from paper_trading.portfolio import Portfolio

logger = logging.getLogger(__name__)


class PerformanceTracker:
    def __init__(self, portfolio: Portfolio):
        self.portfolio = portfolio

    def compute_metrics(self) -> Dict:
        nav_history = self.portfolio.get_nav_history()
        if len(nav_history) < 2:
            return {"note": "Insufficient history for metrics"}

        navs = [e["nav"] for e in nav_history]
        returns = self._pct_returns(navs)
        n_months = len(returns)

        ann_return = self._annualized_return(navs)
        ann_vol = float(np.std(returns) * np.sqrt(12)) if n_months > 1 else 0.0
        sharpe = (ann_return - RISK_FREE_RATE) / ann_vol if ann_vol > 0 else 0.0
        max_dd = self._max_drawdown(navs)
        calmar = ann_return / abs(max_dd) if max_dd != 0 else 0.0
        win_rate = float(np.mean([r > 0 for r in returns])) if returns else 0.0

        metrics = {
            "total_return_pct": round((navs[-1] / INITIAL_CAPITAL_USD - 1) * 100, 2),
            "annualized_return_pct": round(ann_return * 100, 2),
            "annualized_volatility_pct": round(ann_vol * 100, 2),
            "sharpe_ratio": round(sharpe, 4),
            "max_drawdown_pct": round(max_dd * 100, 2),
            "calmar_ratio": round(calmar, 4),
            "win_rate_pct": round(win_rate * 100, 2),
            "best_month_pct": round(float(max(returns)) * 100, 2) if returns else 0,
            "worst_month_pct": round(float(min(returns)) * 100, 2) if returns else 0,
            "current_nav": round(navs[-1], 2),
            "n_months": n_months,
        }
        return metrics

    # ── internals ────────────────────────────────────────────────────────────

    @staticmethod
    def _pct_returns(navs: List[float]) -> List[float]:
        return [(navs[i] / navs[i - 1]) - 1 for i in range(1, len(navs))]

    @staticmethod
    def _annualized_return(navs: List[float]) -> float:
        if len(navs) < 2 or navs[0] <= 0:
            return 0.0
        total_return = navs[-1] / navs[0]
        n_years = (len(navs) - 1) / 12
        if n_years <= 0:
            return 0.0
        return float(total_return ** (1 / n_years) - 1)

    @staticmethod
    def _max_drawdown(navs: List[float]) -> float:
        if len(navs) < 2:
            return 0.0
        peak = navs[0]
        max_dd = 0.0
        for nav in navs[1:]:
            if nav > peak:
                peak = nav
            dd = (nav - peak) / peak
            if dd < max_dd:
                max_dd = dd
        return max_dd
