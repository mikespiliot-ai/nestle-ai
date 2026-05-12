"""
Simulated trade execution for paper trading.
Applies transaction costs, no slippage (conservative assumption).
"""

import logging
from typing import Dict

from config import TRANSACTION_COST_RATE, INITIAL_CAPITAL_USD
from paper_trading.portfolio import Portfolio

logger = logging.getLogger(__name__)


class PaperExecutor:
    def __init__(self, portfolio: Portfolio):
        self.portfolio = portfolio

    # ── monthly rebalancing ──────────────────────────────────────────────────

    def rebalance(self, target_weights: Dict[str, float], price_map: Dict[str, float]):
        """
        Rebalance portfolio to target_weights at current prices.
        target_weights: {symbol: weight (0-1)}
        price_map: {symbol: price_usd}
        """
        nav = self.portfolio.compute_nav(price_map)
        if nav <= 0:
            logger.warning("[Executor] NAV is zero — cannot rebalance")
            return

        current_holdings = self.portfolio.get_holdings()

        # Compute target USD values
        target_values = {sym: w * nav for sym, w in target_weights.items()}

        # Compute current USD values
        current_values = {
            sym: h["quantity"] * price_map.get(sym, 0.0)
            for sym, h in current_holdings.items()
        }

        # Step 1: Sell positions being reduced or removed
        for sym, current_val in current_values.items():
            target_val = target_values.get(sym, 0.0)
            if current_val > target_val and sym in current_holdings:
                sell_val = current_val - target_val
                price = price_map.get(sym, 0.0)
                if price <= 0:
                    continue
                qty_to_sell = sell_val / price
                fee = sell_val * TRANSACTION_COST_RATE
                self.portfolio.update_holding(sym, -qty_to_sell, price)
                self.portfolio.update_cash(sell_val - fee)
                self.portfolio.record_trade(sym, "SELL", qty_to_sell, price, fee)
                logger.debug("[Executor] SELL %s qty=%.6f price=%.2f fee=%.2f", sym, qty_to_sell, price, fee)

        # Step 2: Buy new / increased positions
        for sym, target_val in target_values.items():
            price = price_map.get(sym, 0.0)
            if price <= 0:
                continue
            current_val = current_values.get(sym, 0.0)
            buy_val = target_val - current_val
            if buy_val <= 0:
                continue
            cash = self.portfolio.get_cash()
            buy_val = min(buy_val, cash * 0.99)
            if buy_val <= 0:
                continue
            fee = buy_val * TRANSACTION_COST_RATE
            qty_to_buy = (buy_val - fee) / price
            self.portfolio.update_holding(sym, qty_to_buy, price)
            self.portfolio.update_cash(-(buy_val))
            self.portfolio.record_trade(sym, "BUY", qty_to_buy, price, fee)
            logger.debug("[Executor] BUY  %s qty=%.6f price=%.2f fee=%.2f", sym, qty_to_buy, price, fee)

    # ── emergency actions ────────────────────────────────────────────────────

    def move_to_cash(self, fraction: float, price_map: Dict[str, float]):
        """Liquidate `fraction` of all holdings to cash."""
        holdings = self.portfolio.get_holdings()
        for sym, h in holdings.items():
            price = price_map.get(sym, 0.0)
            if price <= 0:
                continue
            qty_sell = h["quantity"] * fraction
            proceeds = qty_sell * price
            fee = proceeds * TRANSACTION_COST_RATE
            self.portfolio.update_holding(sym, -qty_sell, price)
            self.portfolio.update_cash(proceeds - fee)
            self.portfolio.record_trade(sym, "SELL_EMERGENCY", qty_sell, price, fee)
        self.portfolio.set_mode("DEFENSIVE")
        logger.warning("[Executor] DEFENSIVE: sold %.0f%% of all positions", fraction * 100)

    def reduce_all_positions(self, fraction: float, price_map: Dict[str, float]):
        self.move_to_cash(fraction, price_map)
        self.portfolio.set_mode("REDUCE")

    def reduce_high_beta(self, fraction: float, price_map: Dict[str, float]):
        """
        Reduce holdings with highest volatility (proxy for beta) by `fraction`.
        Uses nav-weighted approach as a proxy for beta.
        """
        holdings = self.portfolio.get_holdings()
        nav = self.portfolio.compute_nav(price_map)
        # Sell the top 50% by value (rough high-beta proxy)
        by_value = sorted(
            [(sym, h["quantity"] * price_map.get(sym, 0.0)) for sym, h in holdings.items()],
            key=lambda x: -x[1],
        )
        top_half = by_value[: max(1, len(by_value) // 2)]
        for sym, _ in top_half:
            h = holdings[sym]
            price = price_map.get(sym, 0.0)
            if price <= 0:
                continue
            qty_sell = h["quantity"] * fraction
            proceeds = qty_sell * price
            fee = proceeds * TRANSACTION_COST_RATE
            self.portfolio.update_holding(sym, -qty_sell, price)
            self.portfolio.update_cash(proceeds - fee)
            self.portfolio.record_trade(sym, "SELL_HEDGE", qty_sell, price, fee)
        logger.warning("[Executor] HEDGE: reduced top-%d positions by %.0f%%", len(top_half), fraction * 100)
