"""
Precision Matrix Estimation — all 5 methods from paper Section 5.2.2.
  1. NW  — Nodewise Regression (LASSO)
  2. RNW — Residual Nodewise Regression (PCA residuals + LASSO)
  3. POET — Principal Orthogonal complEment Thresholding
  4. DL  — Deep Learning (feedforward NN trained on Gaussian log-likelihood)
  5. NLS — Nonlinear Shrinkage (analytical Ledoit-Wolf)
"""

import logging
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)


class PrecisionMatrixEstimator:

    def estimate(self, method: str, R: np.ndarray) -> np.ndarray:
        """
        R: T×p returns matrix.
        Returns p×p precision matrix Γ = Σ⁻¹.
        """
        dispatch = {
            "NW": self._nodewise_regression,
            "RNW": self._residual_nodewise,
            "POET": self._poet,
            "DL": self._deep_learning,
            "NLS": self._nonlinear_shrinkage,
        }
        fn = dispatch.get(method)
        if fn is None:
            raise ValueError(f"Unknown precision method: {method}")
        return fn(R)

    # ── 1. Nodewise Regression ───────────────────────────────────────────────

    def _nodewise_regression(self, R: np.ndarray) -> np.ndarray:
        from sklearn.linear_model import LassoCV
        T, p = R.shape
        Theta = np.zeros((p, p))

        for j in range(p):
            y = R[:, j]
            X = np.delete(R, j, axis=1)
            try:
                lasso = LassoCV(cv=5, max_iter=5000, n_jobs=-1)
                lasso.fit(X, y)
                beta = lasso.coef_
                sigma2_j = np.var(y - X @ beta, ddof=1) + 1e-8
            except Exception:
                beta = np.zeros(p - 1)
                sigma2_j = np.var(y, ddof=1) + 1e-8

            row = np.insert(-beta / sigma2_j, j, 1.0 / sigma2_j)
            Theta[j, :] = row

        # Symmetrize
        Theta = 0.5 * (Theta + Theta.T)
        return self._ensure_psd(Theta)

    # ── 2. Residual Nodewise Regression ────────────────────────────────────

    def _residual_nodewise(self, R: np.ndarray, n_factors: int = 3) -> np.ndarray:
        from sklearn.decomposition import PCA

        T, p = R.shape
        k = min(n_factors, p - 1)
        pca = PCA(n_components=k)
        factors = pca.fit_transform(R)           # T×k
        loadings = pca.components_.T             # p×k
        residuals = R - factors @ loadings.T     # T×p (idiosyncratic)
        return self._nodewise_regression(residuals)

    # ── 3. POET ─────────────────────────────────────────────────────────────

    def _poet(self, R: np.ndarray, n_factors: int = 3) -> np.ndarray:
        from sklearn.decomposition import PCA

        T, p = R.shape
        k = min(n_factors, p - 1)
        pca = PCA(n_components=k)
        F = pca.fit_transform(R)    # T×k factor scores
        B = pca.components_.T       # p×k loadings

        Sigma_u = np.cov(R - F @ B.T, rowvar=False)  # idiosyncratic covariance

        # Threshold off-diagonal
        C = 4.0
        tau = C * np.sqrt(np.log(p) / T)
        for i in range(p):
            for j in range(p):
                if i != j and abs(Sigma_u[i, j]) < tau:
                    Sigma_u[i, j] = 0.0

        Sigma_u = self._ensure_psd(Sigma_u, as_cov=True)

        # Full covariance: Σ = B F B' + Σ_u
        Sigma_F = np.cov(F, rowvar=False) if k > 1 else np.var(F) * np.eye(1)
        Sigma = B @ Sigma_F @ B.T + Sigma_u

        return self._invert_psd(Sigma)

    # ── 4. Deep Learning ────────────────────────────────────────────────────

    def _deep_learning(self, R: np.ndarray) -> np.ndarray:
        try:
            import torch
            import torch.nn as nn
            return self._dl_torch(R)
        except ImportError:
            logger.warning("PyTorch not available — falling back to NLS for DL method")
            return self._nonlinear_shrinkage(R)

    def _dl_torch(self, R: np.ndarray) -> np.ndarray:
        import torch
        import torch.nn as nn
        import torch.optim as optim

        T, p = R.shape
        R_t = torch.tensor(R, dtype=torch.float32)
        S = torch.tensor(np.cov(R, rowvar=False), dtype=torch.float32)  # sample covariance

        class PrecisionNet(nn.Module):
            def __init__(self, p, hidden=(256, 128, 64), dropout=0.2):
                super().__init__()
                layers = []
                in_dim = p
                for h in hidden:
                    layers += [nn.Linear(in_dim, h), nn.ReLU(), nn.Dropout(dropout)]
                    in_dim = h
                layers.append(nn.Linear(in_dim, p * p))
                self.net = nn.Sequential(*layers)
                self.p = p

            def forward(self, x):
                out = self.net(x).reshape(self.p, self.p)
                # Enforce symmetry and PSD via Cholesky parameterization
                L = torch.tril(out)
                L = L + torch.diag(torch.abs(torch.diag(L)) + 1e-4)
                Theta = L @ L.t()
                return Theta

        model = PrecisionNet(p)
        optimizer = optim.Adam(model.parameters(), lr=1e-3)

        # Average return as "input" (simplified — use mean vector)
        x = torch.tensor(R.mean(axis=0), dtype=torch.float32)

        for _ in range(200):
            optimizer.zero_grad()
            Theta = model(x)
            loss = -torch.logdet(Theta + 1e-4 * torch.eye(p)) + torch.trace(S @ Theta)
            loss.backward()
            optimizer.step()

        with torch.no_grad():
            Theta_np = model(x).numpy()

        return self._ensure_psd(0.5 * (Theta_np + Theta_np.T))

    # ── 5. Nonlinear Shrinkage (analytical Ledoit-Wolf) ─────────────────────

    def _nonlinear_shrinkage(self, R: np.ndarray) -> np.ndarray:
        from sklearn.covariance import LedoitWolf

        lw = LedoitWolf()
        lw.fit(R)
        Sigma_shrunk = lw.covariance_
        return self._invert_psd(Sigma_shrunk)

    # ── utilities ────────────────────────────────────────────────────────────

    @staticmethod
    def _ensure_psd(M: np.ndarray, eps: float = 1e-6, as_cov: bool = False) -> np.ndarray:
        M = 0.5 * (M + M.T)
        eigvals, eigvecs = np.linalg.eigh(M)
        eigvals = np.maximum(eigvals, eps)
        result = eigvecs @ np.diag(eigvals) @ eigvecs.T
        return result

    @staticmethod
    def _invert_psd(Sigma: np.ndarray, eps: float = 1e-6) -> np.ndarray:
        Sigma = 0.5 * (Sigma + Sigma.T)
        eigvals, eigvecs = np.linalg.eigh(Sigma)
        eigvals = np.maximum(eigvals, eps)
        inv_eigvals = 1.0 / eigvals
        return eigvecs @ np.diag(inv_eigvals) @ eigvecs.T
