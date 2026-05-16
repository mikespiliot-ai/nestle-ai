"""QuantAgent — runs all 15 method×objective combinations, picks best OOS Sharpe."""

import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from config import (
    DL_EVAL_MONTHS,
    DL_TRAIN_MONTHS,
    PORTFOLIO_OBJECTIVES,
    PRECISION_METHODS,
    RISK_AVERSION_RHO,
    RISK_FREE_RATE,
    ROLLING_WINDOW_MONTHS,
    TARGET_PORTFOLIO_SIZE,
    TRANSACTION_COST_RATE,
)
from memory.claude_flow_store import memory_retrieve, memory_store
from models.precision_matrix import PrecisionMatrixEstimator
from models.portfolio_optimizer import PortfolioOptimizer

logger = logging.getLogger(__name__)


class QuantAgent:
    """Selects the optimal precision/objective combination by OOS Sharpe ratio."""

    def __init__(self, env: Dict[str, Any] = None):
        self.env = env or {}
        self.estimator = PrecisionMatrixEstimator()
        self.optimizer = PortfolioOptimizer()

    def run(self) -> None:
        logger.info("[QuantAgent] Starting quant optimization…")

        returns_dict = memory_retrieve("returns_matrix", {})
        consensus_buys: List[str] = memory_retrieve("consensus_buys", [])
        features: Dict[str, Dict[str, float]] = memory_retrieve("features", {})

        if not returns_dict or not consensus_buys:
            logger.warning("[QuantAgent] No returns data or consensus buys — skipping")
            memory_store("optimal_weights", {})
            memory_store("best_method", "NW_GMV")
            memory_store("all_sharpe_ratios", {})
            return

        # Reconstruct returns DataFrame and filter to selected assets
        try:
            R_full = pd.DataFrame(returns_dict)
        except Exception as exc:
            logger.error("[QuantAgent] Failed to reconstruct returns: %s", exc)
            memory_store("optimal_weights", {})
            return

        # Keep only assets in consensus_buys that have return history
        available = [c for c in consensus_buys if c in R_full.columns]
        if len(available) < 2:
            logger.warning("[QuantAgent] Fewer than 2 assets with history — skipping")
            memory_store("optimal_weights", {self.env.get("fallback", available[0] if available else ""): 1.0})
            return

        R = R_full[available].dropna(how="all").fillna(0.0)
        if len(R) < 6:
            logger.warning("[QuantAgent] Insufficient history rows: %d", len(R))
            eq_w = {c: 1.0 / len(available) for c in available}
            memory_store("optimal_weights", eq_w)
            return

        # Expected returns: mean of z-scored momentum feature
        mu = self._compute_mu(available, features, R)

        # Train/eval split
        train_T = min(DL_TRAIN_MONTHS, max(6, len(R) - DL_EVAL_MONTHS))
        R_train = R.iloc[:train_T]
        R_eval  = R.iloc[train_T:]

        if len(R_eval) == 0:
            R_train, R_eval = R.iloc[: len(R) // 2], R.iloc[len(R) // 2 :]

        # Run all 15 combinations
        sharpe_ratios: Dict[str, float] = {}
        weights_map: Dict[str, np.ndarray] = {}

        for method in PRECISION_METHODS:
            for objective in PORTFOLIO_OBJECTIVES:
                key = f"{method}_{objective}"
                try:
                    Gamma = self.estimator.estimate(method, R_train)
                    w = self.optimizer.optimize(objective, Gamma, mu, RISK_AVERSION_RHO)
                    sharpe = self._oos_sharpe(w, R_eval, available)
                    sharpe_ratios[key] = sharpe
                    weights_map[key] = w
                    logger.debug("[QuantAgent] %s Sharpe=%.4f", key, sharpe)
                except Exception as exc:
                    logger.warning("[QuantAgent] %s failed: %s", key, exc)
                    sharpe_ratios[key] = -99.0

        # Best combination
        best_key = max(sharpe_ratios, key=sharpe_ratios.get)
        best_w = weights_map.get(best_key, np.ones(len(available)) / len(available))

        optimal_weights = {cid: float(w) for cid, w in zip(available, best_w)}

        memory_store("optimal_weights", optimal_weights)
        memory_store("best_method", best_key)
        memory_store("all_sharpe_ratios", sharpe_ratios)

        logger.info(
            "[QuantAgent] Best: %s  Sharpe=%.4f  #assets=%d",
            best_key, sharpe_ratios[best_key], len(available),
        )

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _compute_mu(
        self,
        coin_ids: List[str],
        features: Dict[str, Dict[str, float]],
        R: pd.DataFrame,
    ) -> np.ndarray:
        """Return vector: z-scored momentum + historical mean."""
        mus = []
        for cid in coin_ids:
            hist_mean = float(R[cid].mean()) if cid in R.columns else 0.0
            mom = features.get(cid, {}).get("mom30d", 0.0)
            mus.append(hist_mean + 0.1 * mom)
        return np.array(mus, dtype=float)

    def _oos_sharpe(
        self,
        w: np.ndarray,
        R_eval: pd.DataFrame,
        coin_ids: List[str],
    ) -> float:
        """Compute OOS Sharpe ratio with transaction costs."""
        if R_eval.empty or len(w) == 0:
            return -99.0

        R_mat = R_eval[coin_ids].values  # T_eval x p
        c = TRANSACTION_COST_RATE

        # Gross portfolio returns
        gross = R_mat @ w  # T_eval-vector

        # Approximate turnover: assume we start from equal weight
        p = len(w)
        w_prev = np.ones(p) / p
        turnover = np.sum(np.abs(w - w_prev))

        # Net returns per paper: y_net = y_gross - c * (1 + y_gross) * turnover
        net = gross - c * (1 + gross) * turnover

        if len(net) < 2:
            return float(np.mean(net)) if len(net) == 1 else -99.0

        mean_net = np.mean(net)
        std_net  = np.std(net, ddof=1)
        if std_net < 1e-12:
            return 0.0

        # Annualized (12 months per year)
        sharpe = (mean_net - RISK_FREE_RATE / 12) / std_net * np.sqrt(12)
        return float(sharpe)
