"""Unit tests for precision matrix and portfolio optimizer."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np
import pytest

from models.precision_matrix import PrecisionMatrixEstimator
from models.portfolio_optimizer import PortfolioOptimizer


def make_returns(T=60, p=10, seed=42):
    rng = np.random.default_rng(seed)
    return rng.standard_normal((T, p)) * 0.05


class TestPrecisionMatrix:
    def test_nw_shape_and_symmetry(self):
        R = make_returns()
        est = PrecisionMatrixEstimator()
        G = est.estimate("NW", R)
        assert G.shape == (10, 10)
        assert np.allclose(G, G.T, atol=1e-6)

    def test_nls_psd(self):
        R = make_returns()
        est = PrecisionMatrixEstimator()
        G = est.estimate("NLS", R)
        eigvals = np.linalg.eigvalsh(G)
        assert np.all(eigvals > 0), "NLS precision matrix must be positive definite"

    def test_poet_returns_valid(self):
        R = make_returns()
        est = PrecisionMatrixEstimator()
        G = est.estimate("POET", R)
        assert G.shape == (10, 10)
        assert not np.any(np.isnan(G))

    def test_rnw_returns_valid(self):
        R = make_returns()
        est = PrecisionMatrixEstimator()
        G = est.estimate("RNW", R)
        assert G.shape == (10, 10)


class TestPortfolioOptimizer:
    def setup_method(self):
        R = make_returns()
        from sklearn.covariance import LedoitWolf
        lw = LedoitWolf()
        lw.fit(R)
        Sigma = lw.covariance_
        self.Gamma = np.linalg.inv(Sigma + 1e-4 * np.eye(10))
        self.mu = R.mean(axis=0)
        self.opt = PortfolioOptimizer()

    def test_gmv_sums_to_one(self):
        w = self.opt.optimize("GMV", self.Gamma, self.mu)
        assert abs(w.sum() - 1.0) < 1e-6

    def test_mv_sums_to_one(self):
        w = self.opt.optimize("MV", self.Gamma, self.mu)
        assert abs(w.sum() - 1.0) < 1e-6

    def test_msr_sums_to_one(self):
        w = self.opt.optimize("MSR", self.Gamma, self.mu)
        assert abs(w.sum() - 1.0) < 1e-6

    def test_long_only(self):
        for obj in ["GMV", "MV", "MSR"]:
            w = self.opt.optimize(obj, self.Gamma, self.mu)
            assert np.all(w >= 0), f"{obj}: weights must be non-negative"
