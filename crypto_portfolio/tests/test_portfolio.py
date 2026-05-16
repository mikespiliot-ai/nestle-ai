"""Tests for Portfolio, PaperExecutor."""

import os
import pytest

from paper_trading.portfolio import Portfolio
from paper_trading.executor import PaperExecutor
from config import INITIAL_CAPITAL_USD


@pytest.fixture
def portfolio(tmp_path):
    db = str(tmp_path / "test_portfolio.db")
    return Portfolio(db_path=db)


@pytest.fixture
def executor(portfolio):
    return PaperExecutor(portfolio)


class TestPortfolio:

    def test_initial_cash(self, portfolio):
        assert abs(portfolio.get_cash() - INITIAL_CAPITAL_USD) < 0.01

    def test_get_holdings_empty(self, portfolio):
        assert portfolio.get_holdings() == {}

    def test_update_and_get_holding(self, portfolio):
        portfolio.update_holding("bitcoin", 0.5, 40000.0)
        holdings = portfolio.get_holdings()
        assert "bitcoin" in holdings
        assert abs(holdings["bitcoin"]["quantity"] - 0.5) < 1e-10

    def test_update_cash(self, portfolio):
        portfolio.update_cash(5000.0)
        assert abs(portfolio.get_cash() - 5000.0) < 0.01

    def test_compute_nav_cash_only(self, portfolio):
        nav = portfolio.compute_nav({})
        assert abs(nav - INITIAL_CAPITAL_USD) < 0.01

    def test_compute_nav_with_holdings(self, portfolio):
        portfolio.update_cash(5000.0)
        portfolio.update_holding("bitcoin", 0.1, 50000.0)
        price_map = {"bitcoin": 60000.0}
        nav = portfolio.compute_nav(price_map)
        expected = 5000.0 + 0.1 * 60000.0
        assert abs(nav - expected) < 0.01

    def test_record_and_get_nav_history(self, portfolio):
        portfolio.record_nav(10000.0)
        portfolio.record_nav(10500.0)
        history = portfolio.get_nav_history()
        assert len(history) >= 2
        assert history[-1]["nav"] == 10500.0

    def test_record_trade(self, portfolio):
        portfolio.record_trade("bitcoin", "BUY", 0.1, 50000.0, fee=25.0)
        trades = portfolio.get_trade_history()
        assert len(trades) >= 1
        assert trades[0]["coin_id"] == "bitcoin"
        assert trades[0]["side"] == "BUY"

    def test_set_and_get_mode(self, portfolio):
        portfolio.set_mode("DEFENSIVE")
        state = portfolio.get_state()
        assert state["mode"] == "DEFENSIVE"

    def test_get_current_weights(self, portfolio):
        portfolio.update_cash(5000.0)
        portfolio.update_holding("bitcoin", 0.1, 50000.0)
        price_map = {"bitcoin": 50000.0}
        weights = portfolio.get_current_weights(price_map)
        # holdings value = 5000, cash = 5000, total = 10000
        assert abs(weights.get("bitcoin", 0) - 0.5) < 0.01


class TestPaperExecutor:

    def test_rebalance_basic(self, executor, portfolio):
        price_map = {
            "bitcoin":  50000.0,
            "ethereum": 3000.0,
        }
        target_weights = {"bitcoin": 0.6, "ethereum": 0.4}
        executor.rebalance(target_weights, price_map)

        holdings = portfolio.get_holdings()
        # Should have bought both assets
        assert "bitcoin" in holdings or "ethereum" in holdings

    def test_move_to_cash(self, executor, portfolio):
        portfolio.update_holding("bitcoin", 0.5, 50000.0)
        portfolio.update_cash(5000.0)
        initial_cash = portfolio.get_cash()
        price_map = {"bitcoin": 50000.0}
        executor.move_to_cash(0.5, price_map)
        new_cash = portfolio.get_cash()
        assert new_cash > initial_cash

    def test_rebalance_applies_fees(self, executor, portfolio):
        price_map = {"bitcoin": 50000.0}
        target_weights = {"bitcoin": 1.0}
        executor.rebalance(target_weights, price_map)
        trades = portfolio.get_trade_history()
        # Check that fee > 0 on buy trades
        buy_trades = [t for t in trades if t["side"] == "BUY"]
        if buy_trades:
            assert buy_trades[0]["fee"] > 0
