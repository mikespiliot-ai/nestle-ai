"""
Portfolio Optimization — 3 objectives using precision matrix.
  1. GMV — Global Minimum Variance
  2. MV  — Mean-Variance (risk aversion ρ)
  3. MSR — Maximum Sharpe Ratio
"""

import numpy as np


class PortfolioOptimizer:

    def optimize(
        self,
        objective: str,
        Gamma: np.ndarray,
        mu: np.ndarray,
        rho: float = 0.01,
    ) -> np.ndarray:
        dispatch = {
            "GMV": self._gmv,
            "MV": self._mv,
            "MSR": self._msr,
        }
        fn = dispatch.get(objective)
        if fn is None:
            raise ValueError(f"Unknown objective: {objective}")
        w = fn(Gamma, mu, rho)
        return self._clean_weights(w, len(mu))

    # ── 1. Global Minimum Variance ───────────────────────────────────────────

    @staticmethod
    def _gmv(Gamma: np.ndarray, mu: np.ndarray, rho: float) -> np.ndarray:
        ones = np.ones(len(mu))
        numerator = Gamma @ ones
        denominator = float(ones @ Gamma @ ones)
        if abs(denominator) < 1e-10:
            return ones / len(ones)
        return numerator / denominator

    # ── 2. Mean-Variance ────────────────────────────────────────────────────

    @staticmethod
    def _mv(Gamma: np.ndarray, mu: np.ndarray, rho: float) -> np.ndarray:
        p = len(mu)
        ones = np.ones(p)

        A = float(ones @ Gamma @ ones)
        B = float(mu @ Gamma @ ones)
        C = float(mu @ Gamma @ mu)
        D = A * C - B ** 2

        if abs(D) < 1e-10 or abs(A * D - B ** 2) < 1e-10:
            return ones / p

        term1 = (D - rho * B) / (A * D - B ** 2)
        term2 = (rho * A - B) / (A * D - B ** 2)
        w = term1 * (Gamma @ ones) + term2 * (Gamma @ mu)
        w_sum = w.sum()
        return w / w_sum if abs(w_sum) > 1e-10 else ones / p

    # ── 3. Maximum Sharpe Ratio ──────────────────────────────────────────────

    @staticmethod
    def _msr(Gamma: np.ndarray, mu: np.ndarray, rho: float) -> np.ndarray:
        p = len(mu)
        ones = np.ones(p)
        numerator = Gamma @ mu
        denominator = float(ones @ Gamma @ mu)
        if abs(denominator) < 1e-10:
            return ones / p
        w = numerator / denominator
        w_sum = w.sum()
        return w / w_sum if abs(w_sum) > 1e-10 else ones / p

    # ── utilities ────────────────────────────────────────────────────────────

    @staticmethod
    def _clean_weights(w: np.ndarray, p: int) -> np.ndarray:
        # Clip to [0, 1] — long-only constraint
        w = np.clip(w, 0.0, 1.0)
        total = w.sum()
        if total <= 1e-10:
            return np.ones(p) / p
        return w / total
