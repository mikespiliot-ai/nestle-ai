"""PaperExecutor — simulates trade execution against the Portfolio."""

import logging
from typing import Dict, List

from config import TRANSACTION_COST_RATE
from paper_trading.portfolio import Portfolio

logger = logging.getLogger(__name__)


class PaperExecutor:
    """Simulates order execution for paper trading."""

    def __init__(self, portfolio: Portfolio):
        self._p = portfolio

    # ── Rebalance ─────────────────────────────────────────────────────────────

    def rebalance(
        self, target_weights: Dict[str, float], price_map: Dict[str, float]
    ) -> None:
        """Rebalance to target weights using simulated market orders."""
        nav = self._p.compute_nav(price_map)
        if nav <= 0:
            logger.warning("[PaperExecutor] NAV is zero; skipping rebalance")
            return

        holdings = self._p.get_holdings()
        cash = self._p.get_cash()

        # Determine target values
        target_values: Dict[str, float] = {
            cid: w * nav for cid, w in target_weights.items() if w > 0
        }

        # Sell first (free up cash)
        for cid, h in holdings.items():
            current_val = h["quantity"] * price_map.get(cid, 0.0)
            target_val = target_values.get(cid, 0.0)
            if current_val > target_val + 1.0:  # $1 tolerance
                sell_val = current_val - target_val
                price = price_map.get(cid, 1.0)
                if price <= 0:
                    continue
                qty_sell = sell_val / price
                fee = sell_val * TRANSACTION_COST_RATE
                proceeds = sell_val - fee
                new_qty = h["quantity"] - qty_sell
                self._p.update_holding(cid, max(0.0, new_qty), h["avg_cost"])
                cash += proceeds
                self._p.record_trade(cid, "SELL", qty_sell, price, fee)
                logger.debug("[PaperExecutor] SELL %s qty=%.6f val=%.2f", cid, qty_sell, sell_val)

        self._p.update_cash(cash)

        # Buy
        for cid, target_val in target_values.items():
            price = price_map.get(cid, 0.0)
            if price <= 0:
                continue
            current_qty = holdings.get(cid, {}).get("quantity", 0.0)
            current_val = current_qty * price
            if target_val > current_val + 1.0:
                buy_val = min(target_val - current_val, cash)
                if buy_val < 1.0:
                    continue
                fee = buy_val * TRANSACTION_COST_RATE
                net_buy = buy_val - fee
                qty_buy = net_buy / price
                cash -= buy_val
                if cash < 0:
                    cash = 0.0
                prev_qty = holdings.get(cid, {}).get("quantity", 0.0)
                prev_cost = holdings.get(cid, {}).get("avg_cost", price)
                new_qty = prev_qty + qty_buy
                new_avg = (prev_qty * prev_cost + qty_buy * price) / new_qty if new_qty > 0 else price
                self._p.update_holding(cid, new_qty, new_avg)
                self._p.record_trade(cid, "BUY", qty_buy, price, fee)
                logger.debug("[PaperExecutor] BUY %s qty=%.6f val=%.2f", cid, qty_buy, buy_val)

        self._p.update_cash(max(0.0, cash))
        logger.info("[PaperExecutor] Rebalance complete. Cash remaining: %.2f", self._p.get_cash())

    # ── Emergency actions ─────────────────────────────────────────────────────

    def move_to_cash(self, fraction: float, price_map: Dict[str, float]) -> None:
        """Liquidate *fraction* of all positions to cash."""
        holdings = self._p.get_holdings()
        cash = self._p.get_cash()

        for cid, h in holdings.items():
            qty_sell = h["quantity"] * fraction
            price = price_map.get(cid, 0.0)
            if price <= 0 or qty_sell <= 0:
                continue
            sell_val = qty_sell * price
            fee = sell_val * TRANSACTION_COST_RATE
            proceeds = sell_val - fee
            new_qty = h["quantity"] - qty_sell
            self._p.update_holding(cid, max(0.0, new_qty), h["avg_cost"])
            cash += proceeds
            self._p.record_trade(cid, "SELL", qty_sell, price, fee)

        self._p.update_cash(cash)
        logger.warning("[PaperExecutor] Moved %.0f%% to cash. New cash: %.2f", fraction * 100, cash)

    def reduce_all_positions(self, fraction: float, price_map: Dict[str, float]) -> None:
        """Reduce all positions by *fraction*."""
        self.move_to_cash(fraction, price_map)

    def reduce_high_beta(self, fraction: float, price_map: Dict[str, float]) -> None:
        """Reduce high-beta (small-cap) positions by *fraction*."""
        holdings = self._p.get_holdings()
        cash = self._p.get_cash()

        # Proxy for high beta: holdings with lower price (rougher heuristic)
        prices = {cid: price_map.get(cid, 0.0) for cid in holdings}
        median_price = sorted(prices.values())[len(prices) // 2] if prices else 1.0

        for cid, h in holdings.items():
            price = prices.get(cid, 0.0)
            if price <= 0:
                continue
            # High beta = price below median
            if price < median_price:
                qty_sell = h["quantity"] * fraction
                sell_val = qty_sell * price
                fee = sell_val * TRANSACTION_COST_RATE
                proceeds = sell_val - fee
                new_qty = h["quantity"] - qty_sell
                self._p.update_holding(cid, max(0.0, new_qty), h["avg_cost"])
                cash += proceeds
                self._p.record_trade(cid, "SELL", qty_sell, price, fee)

        self._p.update_cash(cash)
        logger.warning("[PaperExecutor] Reduced high-beta positions. Cash: %.2f", cash)
