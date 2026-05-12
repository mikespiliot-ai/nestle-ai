"""Unit tests for paper trading portfolio."""

import sys, os, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from paper_trading.portfolio import Portfolio
from paper_trading.executor import PaperExecutor


@pytest.fixture
def portfolio(tmp_path):
    db = str(tmp_path / "test_portfolio.db")
    return Portfolio(db_path=db)


def test_initial_cash(portfolio):
    from config import INITIAL_CAPITAL_USD
    assert abs(portfolio.get_cash() - INITIAL_CAPITAL_USD) < 0.01


def test_buy_increases_holding(portfolio):
    portfolio.update_holding("BTC", 0.5, 30000.0)
    portfolio.update_cash(-15000.0)
    h = portfolio.get_holdings()
    assert "BTC" in h
    assert abs(h["BTC"]["quantity"] - 0.5) < 1e-9


def test_sell_reduces_holding(portfolio):
    portfolio.update_holding("BTC", 1.0, 30000.0)
    portfolio.update_holding("BTC", -0.3, 32000.0)
    h = portfolio.get_holdings()
    assert abs(h["BTC"]["quantity"] - 0.7) < 1e-9


def test_nav_computation(portfolio):
    portfolio.update_holding("BTC", 0.1, 50000.0)
    portfolio.update_cash(-5000.0)
    prices = {"BTC": 60000.0}
    nav = portfolio.compute_nav(prices)
    # Cash reduced by 5000, holdings worth 6000 → nav = initial - 5000 + 6000
    from config import INITIAL_CAPITAL_USD
    expected = INITIAL_CAPITAL_USD - 5000.0 + 6000.0
    assert abs(nav - expected) < 0.01


def test_rebalance_executor(portfolio):
    executor = PaperExecutor(portfolio)
    target = {"BTC": 0.5, "ETH": 0.5}
    prices = {"BTC": 50000.0, "ETH": 3000.0}
    executor.rebalance(target, prices)
    h = portfolio.get_holdings()
    assert "BTC" in h or "ETH" in h
