"""Mean-variance portfolio optimizer supporting GMV, MV, and MSR objectives."""

import logging

import numpy as np

logger = logging.getLogger(__name__)


class PortfolioOptimizer:
    """Computes optimal portfolio weights given a precision matrix and return vector.

    Supported objectives:
    - GMV  : Global Minimum Variance
    - MV   : Mean-Variance (with risk aversion rho)
    - MSR  : Maximum Sharpe Ratio (tangency portfolio)
    """

    def optimize(
        self,
        objective: str,
        Gamma: np.ndarray,
        mu: np.ndarray,
        rho: float = 0.01,
    ) -> np.ndarray:
        """Compute portfolio weights.

        Parameters
        ----------
        objective : str
            'GMV', 'MV', or 'MSR'.
        Gamma : np.ndarray
            p x p precision matrix (inverse covariance).
        mu : np.ndarray
            p-vector of expected returns.
        rho : float
            Risk aversion coefficient (used only for MV).

        Returns
        -------
        np.ndarray
            p-vector of portfolio weights summing to 1 in [0, 1].
        """
        objective = objective.upper()
        p = Gamma.shape[0]
        ones = np.ones(p)

        if objective == "GMV":
            w = self._gmv(Gamma, ones)
        elif objective == "MV":
            w = self._mv(Gamma, mu, ones, rho)
        elif objective == "MSR":
            w = self._msr(Gamma, mu, ones)
        else:
            raise ValueError(f"Unknown portfolio objective: {objective}")

        return self._clean_weights(w)

    # ── Objective implementations ─────────────────────────────────────────────

    def _gmv(self, Gamma: np.ndarray, ones: np.ndarray) -> np.ndarray:
        """Global Minimum Variance: w = Gamma @ 1 / (1^T Gamma 1)."""
        num = Gamma @ ones
        denom = ones @ num
        if abs(denom) < 1e-12:
            return ones / len(ones)
        return num / denom

    def _mv(
        self,
        Gamma: np.ndarray,
        mu: np.ndarray,
        ones: np.ndarray,
        rho: float,
    ) -> np.ndarray:
        """Mean-Variance tangency with risk aversion.

        Uses the analytical solution based on scalars A, B, C, D:
          A = 1^T Gamma mu
          B = mu^T Gamma mu
          C = 1^T Gamma 1
          D = B*C - A^2

        w_MV = (1/rho) * (B*Gamma@1 - A*Gamma@mu) / D + (C*Gamma@mu - A*Gamma@1) / (A*D) ...

        Simplified form: w = Gamma @ (mu - lambda*1) / (2*rho)
        where lambda chosen so weights sum to 1.
        """
        Gamma_ones = Gamma @ ones
        Gamma_mu = Gamma @ mu

        A = float(ones @ Gamma_mu)
        B = float(mu @ Gamma_mu)
        C = float(ones @ Gamma_ones)
        D = B * C - A ** 2

        if abs(D) < 1e-12 or abs(C) < 1e-12:
            return self._gmv(Gamma, ones)

        # w = (1/(2*rho)) * [Gamma@mu - (A/C)*Gamma@1] + (1/C)*Gamma@1
        # This is the unconstrained MV frontier solution
        w_gmv = Gamma_ones / C
        w_speculative = Gamma_mu - (A / C) * Gamma_ones
        w = w_gmv + (1.0 / (2.0 * rho)) * w_speculative
        return w

    def _msr(
        self,
        Gamma: np.ndarray,
        mu: np.ndarray,
        ones: np.ndarray,
    ) -> np.ndarray:
        """Maximum Sharpe Ratio (tangency): w = Gamma @ mu / (1^T Gamma mu)."""
        num = Gamma @ mu
        denom = float(ones @ num)
        if abs(denom) < 1e-12:
            return self._gmv(Gamma, ones)
        return num / denom

    # ── Post-processing ───────────────────────────────────────────────────────

    def _clean_weights(self, w: np.ndarray) -> np.ndarray:
        """Clip weights to [0, 1] and normalize to sum = 1."""
        w = np.clip(w, 0.0, 1.0)
        total = w.sum()
        if total < 1e-12:
            p = len(w)
            return np.ones(p) / p
        return w / total
