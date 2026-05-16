"""Full pipeline test with synthetic data — no API calls or LLM required."""

import logging
import os
import sys

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

# ── Synthetic data generation ──────────────────────────────────────────────────

N_SYMBOLS = 20
N_MONTHS  = 60
RNG = np.random.default_rng(42)

SYMBOLS = [f"COIN{i:02d}" for i in range(N_SYMBOLS)]
COIN_IDS = [f"coin-{i:02d}" for i in range(N_SYMBOLS)]

dates = pd.date_range("2020-01-31", periods=N_MONTHS, freq="ME")
prices_raw = 100.0 * np.cumprod(1 + RNG.normal(0.02, 0.15, (N_MONTHS, N_SYMBOLS)), axis=0)
returns_df = pd.DataFrame(
    np.log(prices_raw[1:] / prices_raw[:-1]),
    index=dates[1:],
    columns=COIN_IDS,
)


def build_mock_universe():
    universe = []
    for i, cid in enumerate(COIN_IDS):
        universe.append({
            "id":            cid,
            "symbol":        SYMBOLS[i].lower(),
            "name":          f"Coin {i}",
            "market_cap":    float(RNG.integers(1_000_000, 100_000_000_000)),
            "current_price": float(prices_raw[-1, i]),
            "rank":          i + 1,
        })
    return universe


def build_mock_features():
    features = {}
    for cid in COIN_IDS:
        features[cid] = {
            "log_mcap":    float(RNG.normal(0, 1)),
            "vol_to_mcap": float(RNG.normal(0, 1)),
            "mom30d":      float(RNG.normal(0, 1)),
            "nvt_ratio":   float(RNG.normal(0, 1)),
            "realized_vol": float(RNG.normal(0, 1)),
        }
    return features


def build_mock_macro():
    return {
        "fear_greed":   {"value": 55, "value_classification": "Greed"},
        "global_crypto": {
            "total_market_cap_usd":      2.5e12,
            "btc_dominance":             45.0,
            "market_cap_change_24h_pct": 1.2,
        },
        "VIXCLS":    20.0,
        "FEDFUNDS":  5.25,
    }


def build_mock_signals(coin_ids):
    s1_signals  = {cid: RNG.choice(["BUY", "NEUTRAL", "SELL"], p=[0.4, 0.4, 0.2]) for cid in coin_ids}
    s1_strengths = {cid: float(RNG.uniform(0.5, 0.9)) for cid in coin_ids}
    s2_signals  = {cid: RNG.choice(["BUY", "NEUTRAL", "SELL"], p=[0.4, 0.4, 0.2]) for cid in coin_ids}
    s2_scores   = {cid: float(RNG.uniform(-0.5, 0.5)) for cid in coin_ids}
    return s1_signals, s1_strengths, s2_signals, s2_scores


# ── Main dry-run ───────────────────────────────────────────────────────────────

def main():
    from memory.claude_flow_store import memory_store, memory_retrieve

    logger.info("=== MOCK DRY RUN STARTED ===")

    # Inject synthetic data
    universe = build_mock_universe()
    features = build_mock_features()
    macro    = build_mock_macro()
    s1_signals, s1_strengths, s2_signals, s2_scores = build_mock_signals(COIN_IDS)

    memory_store("universe",       universe)
    memory_store("coin_ids",       COIN_IDS)
    memory_store("returns_matrix", returns_df.to_dict())
    memory_store("features",       features)
    memory_store("macro_data",     macro)
    memory_store("s1_signals",     {k: str(v) for k, v in s1_signals.items()})
    memory_store("s1_strengths",   s1_strengths)
    memory_store("s2_signals",     {k: str(v) for k, v in s2_signals.items()})
    memory_store("s2_scores",      s2_scores)

    # Price map
    price_map = {c["id"]: c["current_price"] for c in universe}
    memory_store("price_map", price_map)

    # MacroAgent
    from agents.macro_agent import MacroAgent
    MacroAgent({}).run()
    logger.info("MacroAgent done. Regime: %s", memory_retrieve("macro_regime"))

    # ConsensusAgent
    from agents.consensus_agent import ConsensusAgent
    ConsensusAgent({}).run()
    buys = memory_retrieve("consensus_buys", [])
    logger.info("ConsensusAgent done. Buys: %d assets", len(buys))

    # QuantAgent
    from agents.quant_agent import QuantAgent
    QuantAgent({}).run()
    best = memory_retrieve("best_method", "N/A")
    weights = memory_retrieve("optimal_weights", {})
    logger.info("QuantAgent done. Best: %s  Assets: %d", best, len(weights))

    # Paper trading rebalance
    from config import PAPER_TRADING_DB
    from paper_trading.portfolio import Portfolio
    from paper_trading.executor import PaperExecutor

    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), PAPER_TRADING_DB)
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    portfolio = Portfolio(db_path)
    executor  = PaperExecutor(portfolio)

    if weights:
        executor.rebalance(weights, price_map)
        logger.info("Rebalance done. Cash: %.2f", portfolio.get_cash())

    nav = portfolio.compute_nav(price_map)
    portfolio.record_nav(nav)
    logger.info("NAV: %.2f", nav)

    # Performance metrics
    from paper_trading.performance import PerformanceTracker
    metrics = PerformanceTracker(portfolio).compute_metrics()
    memory_store("performance_metrics", metrics)
    logger.info("Metrics: %s", metrics)

    # Dashboard
    from reports.dashboard import generate_dashboard
    state = portfolio.get_state()
    mem_data = {
        "nav_history":       portfolio.get_nav_history(),
        "all_sharpe_ratios": memory_retrieve("all_sharpe_ratios", {}),
        "consensus_buys":    buys,
        "consensus_sells":   memory_retrieve("consensus_sells", []),
        "best_method":       best,
        "macro_regime":      memory_retrieve("macro_regime", "NORMAL"),
        "macro_score":       memory_retrieve("macro_score", 0.0),
        "alert_log":         [],
    }
    dash = generate_dashboard(state, metrics, mem_data)
    logger.info("Dashboard: %s", dash)
    logger.info("=== MOCK DRY RUN COMPLETE ===")

    # Print summary
    print("\n" + "=" * 50)
    print("MOCK DRY RUN SUMMARY")
    print("=" * 50)
    print(f"Best method:   {best}")
    print(f"Assets held:   {len(portfolio.get_holdings())}")
    print(f"NAV:           ${nav:.2f}")
    print(f"Sharpe:        {metrics.get('sharpe_ratio', 0):.3f}")
    print(f"Dashboard:     {dash}")


if __name__ == "__main__":
    main()
