"""Precision matrix estimators for portfolio optimization."""

import logging
import warnings
from typing import Optional

import numpy as np
import pandas as pd
from sklearn.linear_model import LassoCV
from sklearn.decomposition import PCA

logger = logging.getLogger(__name__)


class PrecisionMatrixEstimator:
    """Estimates the precision matrix (inverse covariance) using various methods.

    Supported methods: NW, RNW, POET, DL, NLS.
    """

    def estimate(self, method: str, R: pd.DataFrame) -> np.ndarray:
        """Dispatch to the appropriate estimator.

        Parameters
        ----------
        method : str
            One of 'NW', 'RNW', 'POET', 'DL', 'NLS'.
        R : pd.DataFrame
            T x p returns matrix (rows = time, cols = assets).

        Returns
        -------
        np.ndarray
            p x p precision matrix.
        """
        X = R.dropna().values.astype(float)
        p = X.shape[1]

        method = method.upper()
        if method == "NW":
            return self._nodewise_regression(X)
        elif method == "RNW":
            return self._residual_nodewise(X)
        elif method == "POET":
            return self._poet(X)
        elif method == "DL":
            return self._deep_learning(X)
        elif method == "NLS":
            return self._nonlinear_shrinkage(X)
        else:
            raise ValueError(f"Unknown precision method: {method}")

    # ── Estimators ────────────────────────────────────────────────────────────

    def _nodewise_regression(self, X: np.ndarray) -> np.ndarray:
        """Nodewise (LASSO) regression — Meinshausen & Buhlmann (2006)."""
        T, p = X.shape
        C = np.zeros((p, p))
        for j in range(p):
            y = X[:, j]
            others = np.delete(X, j, axis=1)
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    lasso = LassoCV(cv=3, max_iter=5000, n_jobs=1).fit(others, y)
                coef = lasso.coef_
            except Exception:
                coef = np.zeros(p - 1)
            row = np.insert(-coef, j, 1.0)
            C[j, :] = row

        # symmetrize: Theta_ij = sign(C_ij + C_ji) * sqrt(|C_ij * C_ji|)
        Theta = np.zeros((p, p))
        for i in range(p):
            for j in range(p):
                val = C[i, j] * C[j, i]
                Theta[i, j] = np.sign(C[i, j] + C[j, i]) * np.sqrt(abs(val))
        return self._ensure_psd(Theta)

    def _residual_nodewise(self, X: np.ndarray) -> np.ndarray:
        """PCA factor-model residuals then nodewise regression."""
        from config import PCA_FACTORS
        T, p = X.shape
        k = min(PCA_FACTORS, p - 1, T - 1)
        pca = PCA(n_components=k)
        try:
            scores = pca.fit_transform(X)
            loadings = pca.components_.T
            residuals = X - scores @ loadings.T
        except Exception:
            residuals = X
        return self._nodewise_regression(residuals)

    def _poet(self, X: np.ndarray) -> np.ndarray:
        """POET estimator — Fan, Liao & Mincheva (2013)."""
        from config import PCA_FACTORS
        T, p = X.shape
        k = min(PCA_FACTORS, p - 1, T - 1)
        S = np.cov(X, rowvar=False)

        # Factor decomposition
        eigvals, eigvecs = np.linalg.eigh(S)
        idx = np.argsort(eigvals)[::-1]
        eigvals, eigvecs = eigvals[idx], eigvecs[:, idx]
        F = eigvecs[:, :k]
        Lambda = np.diag(eigvals[:k])
        systematic = F @ Lambda @ F.T

        # Idiosyncratic covariance (thresholded)
        sigma_u = S - systematic
        # Adaptive thresholding
        diag = np.sqrt(np.diag(sigma_u))
        with np.errstate(divide="ignore", invalid="ignore"):
            corr_u = sigma_u / np.outer(diag, diag)
        corr_u = np.nan_to_num(corr_u)
        threshold = np.sqrt(np.log(p) / T)
        corr_u_thresh = np.where(np.abs(corr_u) > threshold, corr_u, 0.0)
        sigma_u_thresh = corr_u_thresh * np.outer(diag, diag)
        np.fill_diagonal(sigma_u_thresh, np.diag(sigma_u))

        Sigma_poet = systematic + sigma_u_thresh
        return self._invert_psd(self._ensure_psd(Sigma_poet))

    def _deep_learning(self, X: np.ndarray) -> np.ndarray:
        """Deep learning Cholesky parameterization. Falls back to NLS if torch unavailable."""
        try:
            import torch
            import torch.nn as nn
            from config import DL_HIDDEN_LAYERS, DL_DROPOUT
        except ImportError:
            logger.warning("PyTorch unavailable; falling back to NLS for DL method.")
            return self._nonlinear_shrinkage(X)

        T, p = X.shape
        X_tensor = torch.tensor(X, dtype=torch.float32)

        class CholNet(nn.Module):
            def __init__(self, in_dim, hidden, dropout, out_dim):
                super().__init__()
                layers = []
                prev = in_dim
                for h in hidden:
                    layers += [nn.Linear(prev, h), nn.ReLU(), nn.Dropout(dropout)]
                    prev = h
                self.net = nn.Sequential(*layers)
                self.out = nn.Linear(prev, out_dim)

            def forward(self, x):
                return self.out(self.net(x))

        n_chol = p * (p + 1) // 2
        net = CholNet(p, DL_HIDDEN_LAYERS, DL_DROPOUT, n_chol)
        optimizer = torch.optim.Adam(net.parameters(), lr=1e-3)

        # Simple self-supervised: predict covariance diagonal from returns
        try:
            for _ in range(200):
                optimizer.zero_grad()
                out = net(X_tensor)
                # Reconstruct Cholesky
                L = torch.zeros(p, p)
                tril_idx = torch.tril_indices(p, p)
                L[tril_idx[0], tril_idx[1]] = out.mean(0)
                L_diag = torch.diag(L)
                L = L - torch.diag(L_diag) + torch.diag(torch.exp(L_diag))
                Sigma = L @ L.T
                # Loss: NLL of Gaussian
                try:
                    dist = torch.distributions.MultivariateNormal(
                        torch.zeros(p), covariance_matrix=Sigma + 1e-4 * torch.eye(p)
                    )
                    loss = -dist.log_prob(X_tensor).mean()
                except Exception:
                    loss = torch.tensor(0.0, requires_grad=True)
                loss.backward()
                optimizer.step()

            with torch.no_grad():
                out = net(X_tensor).mean(0)
                L = torch.zeros(p, p)
                tril_idx = torch.tril_indices(p, p)
                L[tril_idx[0], tril_idx[1]] = out
                L_diag = torch.diag(L)
                L = L - torch.diag(L_diag) + torch.diag(torch.exp(L_diag))
                Sigma = (L @ L.T).numpy()
        except Exception as e:
            logger.warning("DL estimator failed (%s); falling back to NLS.", e)
            return self._nonlinear_shrinkage(X)

        return self._invert_psd(self._ensure_psd(Sigma))

    def _nonlinear_shrinkage(self, X: np.ndarray) -> np.ndarray:
        """Ledoit-Wolf shrinkage (sklearn implementation)."""
        from sklearn.covariance import LedoitWolf
        try:
            lw = LedoitWolf().fit(X)
            Sigma = lw.covariance_
        except Exception:
            Sigma = np.cov(X, rowvar=False)
        return self._invert_psd(self._ensure_psd(Sigma))

    # ── Utilities ─────────────────────────────────────────────────────────────

    def _ensure_psd(self, M: np.ndarray, eps: float = 1e-6) -> np.ndarray:
        """Regularize M to be positive semi-definite."""
        M = (M + M.T) / 2
        eigvals, eigvecs = np.linalg.eigh(M)
        eigvals = np.maximum(eigvals, eps)
        return eigvecs @ np.diag(eigvals) @ eigvecs.T

    def _invert_psd(self, Sigma: np.ndarray, eps: float = 1e-6) -> np.ndarray:
        """Numerically stable inversion of a PSD matrix."""
        try:
            return np.linalg.inv(Sigma + eps * np.eye(Sigma.shape[0]))
        except np.linalg.LinAlgError:
            return np.linalg.pinv(Sigma)
