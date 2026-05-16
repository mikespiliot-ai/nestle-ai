"""PerformanceTracker — computes portfolio performance metrics from NAV history."""

import logging
from typing import Any, Dict, List

import numpy as np

from config import RISK_FREE_RATE
from paper_trading.portfolio import Portfolio

logger = logging.getLogger(__name__)


class PerformanceTracker:
    """Computes performance metrics from the portfolio NAV history."""

    def __init__(self, portfolio: Portfolio):
        self._p = portfolio

    def compute_metrics(self) -> Dict[str, Any]:
        nav_history = self._p.get_nav_history()

        if len(nav_history) < 2:
            return self._empty_metrics(nav_history)

        navs = np.array([r["nav"] for r in nav_history], dtype=float)
        current_nav = float(navs[-1])
        initial_nav = float(navs[0])

        # Monthly returns
        returns = np.diff(navs) / navs[:-1]
        n_months = len(returns)

        total_return = (current_nav / initial_nav - 1) * 100
        ann_return = ((current_nav / initial_nav) ** (12 / max(n_months, 1)) - 1) * 100
        ann_vol = float(np.std(returns, ddof=1) * np.sqrt(12) * 100) if n_months > 1 else 0.0

        # Sharpe ratio
        excess = returns - RISK_FREE_RATE / 12
        sharpe = float(np.mean(excess) / np.std(excess, ddof=1) * np.sqrt(12)) if np.std(excess) > 1e-12 else 0.0

        # Max drawdown
        peak = navs[0]
        max_dd = 0.0
        for nav in navs[1:]:
            if nav > peak:
                peak = nav
            dd = (peak - nav) / peak
            if dd > max_dd:
                max_dd = dd
        max_dd_pct = max_dd * 100

        # Calmar ratio
        calmar = ann_return / max_dd_pct if max_dd_pct > 0 else 0.0

        # Win rate
        win_rate = float(np.mean(returns > 0) * 100) if n_months > 0 else 0.0

        best_month  = float(np.max(returns) * 100)  if n_months > 0 else 0.0
        worst_month = float(np.min(returns) * 100)  if n_months > 0 else 0.0

        return {
            "total_return_pct":      round(total_return, 4),
            "annualized_return_pct": round(ann_return, 4),
            "annualized_volatility_pct": round(ann_vol, 4),
            "sharpe_ratio":          round(sharpe, 4),
            "max_drawdown_pct":      round(max_dd_pct, 4),
            "calmar_ratio":          round(calmar, 4),
            "win_rate_pct":          round(win_rate, 4),
            "best_month_pct":        round(best_month, 4),
            "worst_month_pct":       round(worst_month, 4),
            "current_nav":           round(current_nav, 2),
            "n_months":              n_months,
        }

    def _empty_metrics(self, nav_history: List[Dict]) -> Dict[str, Any]:
        current_nav = nav_history[-1]["nav"] if nav_history else 0.0
        return {
            "total_return_pct":      0.0,
            "annualized_return_pct": 0.0,
            "annualized_volatility_pct": 0.0,
            "sharpe_ratio":          0.0,
            "max_drawdown_pct":      0.0,
            "calmar_ratio":          0.0,
            "win_rate_pct":          0.0,
            "best_month_pct":        0.0,
            "worst_month_pct":       0.0,
            "current_nav":           float(current_nav),
            "n_months":              0,
        }
