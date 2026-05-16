"""Tests for PrecisionMatrixEstimator and PortfolioOptimizer."""

import numpy as np
import pandas as pd
import pytest

from models.precision_matrix import PrecisionMatrixEstimator
from models.portfolio_optimizer import PortfolioOptimizer


@pytest.fixture
def sample_returns():
    rng = np.random.default_rng(0)
    T, p = 60, 8
    R = pd.DataFrame(rng.normal(0.01, 0.05, (T, p)),
                     columns=[f"c{i}" for i in range(p)])
    return R


@pytest.fixture
def estimator():
    return PrecisionMatrixEstimator()


@pytest.fixture
def optimizer():
    return PortfolioOptimizer()


# ── PrecisionMatrixEstimator tests ────────────────────────────────────────────

class TestPrecisionMatrixEstimator:

    def test_nw_shape(self, estimator, sample_returns):
        G = estimator.estimate("NW", sample_returns)
        p = sample_returns.shape[1]
        assert G.shape == (p, p)

    def test_nw_symmetry(self, estimator, sample_returns):
        G = estimator.estimate("NW", sample_returns)
        np.testing.assert_allclose(G, G.T, atol=1e-8)

    def test_nw_psd(self, estimator, sample_returns):
        G = estimator.estimate("NW", sample_returns)
        eigvals = np.linalg.eigvalsh(G)
        assert np.all(eigvals >= -1e-6), f"Negative eigenvalue: {eigvals.min()}"

    def test_nls_shape(self, estimator, sample_returns):
        G = estimator.estimate("NLS", sample_returns)
        p = sample_returns.shape[1]
        assert G.shape == (p, p)

    def test_nls_symmetry(self, estimator, sample_returns):
        G = estimator.estimate("NLS", sample_returns)
        np.testing.assert_allclose(G, G.T, atol=1e-8)

    def test_poet_shape(self, estimator, sample_returns):
        G = estimator.estimate("POET", sample_returns)
        p = sample_returns.shape[1]
        assert G.shape == (p, p)

    def test_rnw_shape(self, estimator, sample_returns):
        G = estimator.estimate("RNW", sample_returns)
        p = sample_returns.shape[1]
        assert G.shape == (p, p)

    def test_invalid_method(self, estimator, sample_returns):
        with pytest.raises(ValueError):
            estimator.estimate("INVALID", sample_returns)


# ── PortfolioOptimizer tests ──────────────────────────────────────────────────

class TestPortfolioOptimizer:

    @pytest.fixture
    def gamma_and_mu(self, sample_returns):
        est = PrecisionMatrixEstimator()
        G = est.estimate("NLS", sample_returns)
        mu = sample_returns.mean().values
        return G, mu

    def test_gmv_sums_to_one(self, optimizer, gamma_and_mu):
        G, mu = gamma_and_mu
        w = optimizer.optimize("GMV", G, mu)
        assert abs(w.sum() - 1.0) < 1e-6

    def test_gmv_non_negative(self, optimizer, gamma_and_mu):
        G, mu = gamma_and_mu
        w = optimizer.optimize("GMV", G, mu)
        assert np.all(w >= -1e-8)

    def test_mv_sums_to_one(self, optimizer, gamma_and_mu):
        G, mu = gamma_and_mu
        w = optimizer.optimize("MV", G, mu, rho=0.01)
        assert abs(w.sum() - 1.0) < 1e-6

    def test_mv_non_negative(self, optimizer, gamma_and_mu):
        G, mu = gamma_and_mu
        w = optimizer.optimize("MV", G, mu, rho=0.01)
        assert np.all(w >= -1e-8)

    def test_msr_sums_to_one(self, optimizer, gamma_and_mu):
        G, mu = gamma_and_mu
        w = optimizer.optimize("MSR", G, mu)
        assert abs(w.sum() - 1.0) < 1e-6

    def test_msr_non_negative(self, optimizer, gamma_and_mu):
        G, mu = gamma_and_mu
        w = optimizer.optimize("MSR", G, mu)
        assert np.all(w >= -1e-8)

    def test_invalid_objective(self, optimizer, gamma_and_mu):
        G, mu = gamma_and_mu
        with pytest.raises(ValueError):
            optimizer.optimize("INVALID", G, mu)
