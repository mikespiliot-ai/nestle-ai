"""
Testnet Executor — rebalances the paper portfolio on Binance Testnet.
Converts target weights → USDT-denominated market orders.
Mirrors the same interface as executor.py so BacktestAgent can use either.
"""

import logging
from typing import Dict, List

from paper_trading.binance_testnet import BinanceTestnetClient
from paper_trading.portfolio import Portfolio
from config import TRANSACTION_COST_RATE, REBALANCE_DRIFT_THRESHOLD

logger = logging.getLogger(__name__)

# Symbols we can trade on testnet (USDT pairs available)
USDT_SUFFIX = "USDT"
# Minimum order size in USDT (Binance testnet minimum)
MIN_ORDER_USDT = 10.0


class TestnetExecutor:
    def __init__(self, client: BinanceTestnetClient, portfolio: Portfolio):
        self.client    = client
        self.portfolio = portfolio

    # ── Rebalance ─────────────────────────────────────────────────────────────

    def rebalance(self, target_weights: Dict[str, float]):
        """
        Rebalance to target_weights using live testnet prices.
        target_weights: {symbol: 0-1 fraction of total portfolio value}
        """
        if not self.client.ping():
            logger.error("[TestnetExecutor] Binance testnet unreachable")
            return

        # Get all current prices in one call
        all_prices = self.client.get_prices()
        price_map  = self._build_price_map(list(target_weights.keys()), all_prices)

        # Current state
        balances = self.client.get_balances()
        usdt_free = balances.get("USDT", 0.0)

        # Portfolio value = USDT + all token holdings marked-to-market
        portfolio_value = usdt_free + sum(
            balances.get(sym, 0.0) * price_map.get(sym, 0.0)
            for sym in target_weights
        )
        if portfolio_value <= 0:
            logger.error("[TestnetExecutor] Portfolio value = 0 — cannot rebalance")
            return

        logger.info("[TestnetExecutor] Portfolio value: $%.2f USDT", portfolio_value)

        # Step 1: Sell what we need to sell (free up USDT)
        for sym, target_w in target_weights.items():
            price = price_map.get(sym, 0.0)
            if price <= 0:
                continue
            current_qty  = balances.get(sym, 0.0)
            current_val  = current_qty * price
            target_val   = target_w * portfolio_value
            sell_val     = current_val - target_val

            if sell_val > MIN_ORDER_USDT:
                sell_qty = sell_val / price
                logger.info("[TestnetExecutor] SELL %s qty=%.6f (~$%.2f)", sym, sell_qty, sell_val)
                result = self.client.market_sell(f"{sym}{USDT_SUFFIX}", sell_qty)
                if result:
                    self.portfolio.record_trade(sym, "SELL", sell_qty, price,
                                                fee=sell_val * TRANSACTION_COST_RATE)

        # Refresh USDT after sells
        balances  = self.client.get_balances()
        usdt_free = balances.get("USDT", 0.0)

        # Step 2: Buy what we need to buy
        for sym, target_w in target_weights.items():
            price = price_map.get(sym, 0.0)
            if price <= 0:
                continue
            current_qty = balances.get(sym, 0.0)
            current_val = current_qty * price
            target_val  = target_w * portfolio_value
            buy_val     = target_val - current_val

            if buy_val > MIN_ORDER_USDT:
                buy_val = min(buy_val, usdt_free * 0.99)
                if buy_val < MIN_ORDER_USDT:
                    continue
                logger.info("[TestnetExecutor] BUY  %s $%.2f USDT", sym, buy_val)
                result = self.client.market_buy(f"{sym}{USDT_SUFFIX}", buy_val)
                if result:
                    filled_qty = float(result.get("executedQty", 0))
                    self.portfolio.record_trade(sym, "BUY", filled_qty, price,
                                                fee=buy_val * TRANSACTION_COST_RATE)
                    usdt_free -= buy_val

        # Sync portfolio DB with actual testnet balances
        self._sync_portfolio(target_weights, price_map)

    # ── Emergency actions ─────────────────────────────────────────────────────

    def move_to_cash(self, fraction: float):
        """Liquidate `fraction` of every token holding to USDT."""
        all_prices = self.client.get_prices()
        balances   = self.client.get_balances()

        for sym, qty in balances.items():
            if sym == "USDT" or qty <= 0:
                continue
            price = all_prices.get(f"{sym}{USDT_SUFFIX}", 0.0)
            if price <= 0:
                continue
            sell_qty = qty * fraction
            sell_val = sell_qty * price
            if sell_val < MIN_ORDER_USDT:
                continue
            logger.warning("[TestnetExecutor] EMERGENCY SELL %s qty=%.6f", sym, sell_qty)
            self.client.market_sell(f"{sym}{USDT_SUFFIX}", sell_qty)

        self.portfolio.set_mode("DEFENSIVE")

    # ── Internals ─────────────────────────────────────────────────────────────

    @staticmethod
    def _build_price_map(symbols: List[str], all_prices: Dict[str, float]) -> Dict[str, float]:
        return {sym: all_prices.get(f"{sym}{USDT_SUFFIX}", 0.0) for sym in symbols}

    def _sync_portfolio(self, target_weights: Dict[str, float], price_map: Dict[str, float]):
        """Update local SQLite to reflect actual testnet balances."""
        balances = self.client.get_balances()
        for sym in target_weights:
            qty   = balances.get(sym, 0.0)
            price = price_map.get(sym, 0.0)
            if qty > 0 and price > 0:
                self.portfolio.update_holding(sym, qty - self.portfolio.get_holdings().get(sym, {}).get("quantity", 0), price)

        nav = sum(
            balances.get(sym, 0.0) * price_map.get(sym, 0.0)
            for sym in target_weights
        ) + balances.get("USDT", 0.0)

        self.portfolio.record_nav(nav)
        logger.info("[TestnetExecutor] Synced NAV: $%.2f", nav)
