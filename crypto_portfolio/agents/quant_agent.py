"""
QUANT AGENT — Layer 3
Implements paper Section 5.2.2.
Runs all 5 precision matrix methods × 3 portfolio objectives (15 combinations).
Selects the combination with the highest out-of-sample Sharpe ratio.
"""

import logging
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from config import (
    ROLLING_WINDOW_MONTHS,
    RISK_AVERSION_RHO,
    TRANSACTION_COST_RATE,
    DL_TRAIN_MONTHS,
    DL_EVAL_MONTHS,
    PRECISION_METHODS,
    PORTFOLIO_OBJECTIVES,
)
from models.precision_matrix import PrecisionMatrixEstimator
from models.portfolio_optimizer import PortfolioOptimizer
from memory.claude_flow_store import memory_store, memory_retrieve

logger = logging.getLogger(__name__)


class QuantAgent:
    def run(self):
        logger.info("[QuantAgent] Starting optimization")

        selected: List[str] = memory_retrieve("selected_universe", [])
        price_history: Dict = memory_retrieve("price_history", {})
        universe_list: List[Dict] = memory_retrieve("universe_list", [])

        if not selected:
            logger.error("[QuantAgent] No selected_universe — aborting")
            return

        # Map symbols to coin_ids
        sym_to_id = {c["symbol"]: c["id"] for c in universe_list}
        coin_ids = [sym_to_id[s] for s in selected if s in sym_to_id]

        if len(coin_ids) < 3:
            logger.error("[QuantAgent] Too few assets (%d) — aborting", len(coin_ids))
            return

        # Build returns matrix
        returns_dict = {cid: price_history[cid] for cid in coin_ids if cid in price_history}
        if not returns_dict:
            logger.error("[QuantAgent] No return data available — aborting")
            return

        df = pd.DataFrame(returns_dict).dropna(how="all")
        df = df.fillna(0.0)

        # Align length to rolling window
        T = min(len(df), ROLLING_WINDOW_MONTHS)
        df = df.tail(T)

        R = df.values.astype(float)  # T × p
        mu = R.mean(axis=0)
        p = R.shape[1]

        # Split for OOS evaluation
        train_T = DL_TRAIN_MONTHS
        eval_T = DL_EVAL_MONTHS
        R_train = R[:train_T] if len(R) > train_T else R
        R_eval = R[train_T:train_T + eval_T] if len(R) > train_T else R

        estimator = PrecisionMatrixEstimator()
        optimizer = PortfolioOptimizer()

        best_sharpe = -np.inf
        best_weights: Optional[Dict[str, float]] = None
        best_method_name = ""
        sharpe_table: Dict[str, float] = {}

        prev_weights = np.ones(p) / p  # Equal weight as starting point

        for method in PRECISION_METHODS:
            try:
                Gamma = estimator.estimate(method, R_train)
            except Exception as e:
                logger.warning("[QuantAgent] Precision method %s failed: %s", method, e)
                continue

            for obj in PORTFOLIO_OBJECTIVES:
                try:
                    w = optimizer.optimize(obj, Gamma, mu, rho=RISK_AVERSION_RHO)
                except Exception as e:
                    logger.warning("[QuantAgent] Objective %s failed: %s", obj, e)
                    continue

                # Compute OOS net Sharpe
                sharpe = self._oos_sharpe(w, prev_weights, R_eval)
                key = f"{method}_{obj}"
                sharpe_table[key] = round(float(sharpe), 4)

                if sharpe > best_sharpe:
                    best_sharpe = sharpe
                    best_weights = dict(zip(coin_ids, w.tolist()))
                    best_method_name = key

        if best_weights is None:
            logger.warning("[QuantAgent] All methods failed — using equal weights")
            best_weights = {cid: 1.0 / len(coin_ids) for cid in coin_ids}
            best_method_name = "EQUAL"

        # Convert coin_id keys to symbols for downstream use
        id_to_sym = {v: k for k, v in sym_to_id.items()}
        sym_weights = {id_to_sym.get(cid, cid): w for cid, w in best_weights.items()}

        logger.info("[QuantAgent] Best: %s  Sharpe=%.4f", best_method_name, best_sharpe)
        memory_store("optimal_weights", sym_weights)
        memory_store("best_method", best_method_name)
        memory_store("all_sharpe_ratios", sharpe_table)

    # ── OOS Sharpe with transaction costs ──────────────────────────────────

    def _oos_sharpe(
        self,
        w_new: np.ndarray,
        w_prev: np.ndarray,
        R_eval: np.ndarray,
    ) -> float:
        if len(R_eval) == 0:
            return 0.0

        net_returns = []
        w_current = w_prev.copy()

        for t in range(len(R_eval)):
            r_t = R_eval[t]
            y_gross = float(w_current @ r_t)

            # Transaction cost formula from paper
            denom = (1 + y_gross) if (1 + y_gross) != 0 else 1e-6
            turnover = np.sum(np.abs(w_new - w_current * (1 + r_t) / denom))
            y_net = y_gross - TRANSACTION_COST_RATE * (1 + y_gross) * turnover
            net_returns.append(y_net)

            # Drift weights after returns
            w_current = w_current * (1 + r_t)
            wsum = w_current.sum()
            w_current = w_current / wsum if wsum > 0 else w_new.copy()

        rets = np.array(net_returns)
        if rets.std() == 0:
            return 0.0
        return float(rets.mean() / rets.std() * np.sqrt(12))
