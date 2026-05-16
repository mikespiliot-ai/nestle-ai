"""TestnetExecutor — rebalances via Binance Testnet and syncs local SQLite."""

import logging
from typing import Any, Dict, Optional

from config import TRANSACTION_COST_RATE
from paper_trading.binance_testnet import BinanceTestnetClient
from paper_trading.portfolio import Portfolio

logger = logging.getLogger(__name__)

MIN_ORDER_USDT = 10.0


class TestnetExecutor:
    """Executes real orders on Binance Testnet and keeps the local portfolio in sync."""

    def __init__(self, client: BinanceTestnetClient, portfolio: Portfolio):
        self._client = client
        self._p = portfolio

    # ── Rebalance ─────────────────────────────────────────────────────────────

    def rebalance(self, target_weights: Dict[str, float]) -> None:
        """Rebalance portfolio to target weights on Binance Testnet."""
        # Fetch live prices
        all_prices = self._client.get_prices()
        balances = self._client.get_balances()

        usdt_balance = balances.get("USDT", 0.0)

        # Compute portfolio value (USDT + holdings)
        portfolio_value = usdt_balance
        coin_balances: Dict[str, float] = {}
        for asset, qty in balances.items():
            if asset == "USDT":
                continue
            symbol = asset + "USDT"
            price = all_prices.get(symbol, 0.0)
            if price > 0:
                portfolio_value += qty * price
                coin_balances[asset] = qty

        if portfolio_value <= 0:
            logger.warning("[TestnetExecutor] Portfolio value is zero; skipping rebalance")
            return

        logger.info("[TestnetExecutor] Portfolio value: %.2f USDT", portfolio_value)

        # Compute target values
        target_values: Dict[str, float] = {}
        for cid, w in target_weights.items():
            symbol_upper = cid.upper() + "USDT"
            if w > 0 and symbol_upper in all_prices:
                target_values[cid] = w * portfolio_value

        # Current values
        current_values: Dict[str, float] = {}
        for cid in target_weights:
            asset = cid.upper()
            qty = coin_balances.get(asset, 0.0)
            symbol = asset + "USDT"
            price = all_prices.get(symbol, 0.0)
            current_values[cid] = qty * price

        # Sell excess first
        for cid, target_val in target_values.items():
            current_val = current_values.get(cid, 0.0)
            if current_val > target_val + MIN_ORDER_USDT:
                sell_usdt = current_val - target_val
                asset = cid.upper()
                symbol = asset + "USDT"
                price = all_prices.get(symbol, 1.0)
                qty_sell = sell_usdt / price
                qty_sell = self._client._round_qty(symbol, qty_sell)
                if qty_sell * price >= MIN_ORDER_USDT:
                    result = self._client.market_sell(symbol, qty_sell)
                    if result:
                        logger.info("[TestnetExecutor] SOLD %s qty=%.6f", symbol, qty_sell)
                        self._sync_sell(cid, qty_sell, price)

        # Re-fetch USDT balance after sells
        balances = self._client.get_balances()
        usdt_balance = balances.get("USDT", 0.0)

        # Buy deficits
        for cid, target_val in target_values.items():
            current_val = current_values.get(cid, 0.0)
            if target_val > current_val + MIN_ORDER_USDT:
                buy_usdt = min(target_val - current_val, usdt_balance)
                if buy_usdt < MIN_ORDER_USDT:
                    continue
                asset = cid.upper()
                symbol = asset + "USDT"
                result = self._client.market_buy(symbol, buy_usdt)
                if result:
                    price = all_prices.get(symbol, 1.0)
                    qty_bought = buy_usdt / price * (1 - TRANSACTION_COST_RATE)
                    usdt_balance -= buy_usdt
                    logger.info("[TestnetExecutor] BOUGHT %s usdt=%.2f", symbol, buy_usdt)
                    self._sync_buy(cid, qty_bought, price)

        # Sync cash
        balances = self._client.get_balances()
        self._p.update_cash(balances.get("USDT", 0.0))

    # ── Emergency ─────────────────────────────────────────────────────────────

    def move_to_cash(self, fraction: float, price_map: Optional[Dict] = None) -> None:
        """Sell *fraction* of all non-USDT holdings to cash."""
        balances = self._client.get_balances()
        all_prices = self._client.get_prices()

        for asset, qty in balances.items():
            if asset == "USDT":
                continue
            symbol = asset + "USDT"
            price = all_prices.get(symbol, 0.0)
            if price <= 0:
                continue
            qty_sell = self._client._round_qty(symbol, qty * fraction)
            if qty_sell * price >= MIN_ORDER_USDT:
                result = self._client.market_sell(symbol, qty_sell)
                if result:
                    cid = asset.lower()
                    self._sync_sell(cid, qty_sell, price)

        balances = self._client.get_balances()
        self._p.update_cash(balances.get("USDT", 0.0))

    # ── Sync helpers ──────────────────────────────────────────────────────────

    def _sync_buy(self, cid: str, qty: float, price: float) -> None:
        holdings = self._p.get_holdings()
        prev = holdings.get(cid, {"quantity": 0.0, "avg_cost": price})
        prev_qty = prev["quantity"]
        prev_cost = prev["avg_cost"]
        new_qty = prev_qty + qty
        new_avg = (prev_qty * prev_cost + qty * price) / new_qty if new_qty > 0 else price
        self._p.update_holding(cid, new_qty, new_avg)
        fee = qty * price * TRANSACTION_COST_RATE
        self._p.record_trade(cid, "BUY", qty, price, fee)

    def _sync_sell(self, cid: str, qty: float, price: float) -> None:
        holdings = self._p.get_holdings()
        prev = holdings.get(cid, {"quantity": 0.0, "avg_cost": price})
        new_qty = max(0.0, prev["quantity"] - qty)
        self._p.update_holding(cid, new_qty, prev["avg_cost"])
        fee = qty * price * TRANSACTION_COST_RATE
        self._p.record_trade(cid, "SELL", qty, price, fee)
