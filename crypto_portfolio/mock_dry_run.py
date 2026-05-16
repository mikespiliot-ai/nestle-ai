"""
Mock data dry-run test — exercises the full pipeline without real API calls.
Injects synthetic universe + returns into memory and runs all agents.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import logging
import numpy as np
import random

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("mock_run")

# ── 1. Build synthetic universe and price history ────────────────────────────
from memory.claude_flow_store import memory_store

SYMBOLS = ["BTC", "ETH", "BNB", "SOL", "ADA", "DOT", "AVAX", "MATIC",
           "LINK", "UNI", "ATOM", "LTC", "XRP", "NEAR", "APT",
           "ARB", "OP", "FTM", "INJ", "SUI"]

rng = np.random.default_rng(42)
T = 60  # 60 months of history

universe = [
    {
        "id": sym.lower() + "-mock",
        "symbol": sym,
        "name": sym + " Token",
        "market_cap": int(rng.uniform(1e9, 5e11)),
        "current_price": float(rng.uniform(0.5, 50000)),
        "rank": i + 1,
    }
    for i, sym in enumerate(SYMBOLS)
]
memory_store("universe_list", universe)
logger.info("Universe injected: %d coins", len(universe))

# Synthetic monthly returns (T×p)
returns_raw = rng.standard_normal((T + 1, len(SYMBOLS))) * 0.12 + 0.02
price_history = {}
for i, sym in enumerate(SYMBOLS):
    cid = sym.lower() + "-mock"
    # Monthly returns as list
    price_history[cid] = returns_raw[1:, i].tolist()
memory_store("price_history", price_history)
logger.info("Price history injected: %d months × %d assets", T, len(SYMBOLS))

# Synthetic z-scored features
features = {}
for sym in SYMBOLS:
    features[sym] = {
        "log_mcap_z": float(rng.standard_normal()),
        "vol_to_mcap_z": float(rng.standard_normal()),
        "mom30d_z": float(rng.standard_normal()),
        "nvt_ratio_z": float(rng.standard_normal()),
        "realized_vol_z": float(rng.standard_normal()),
        "log_mcap": float(rng.uniform(20, 27)),
        "vol_to_mcap": float(rng.uniform(0.01, 0.5)),
        "mom30d": float(rng.uniform(-0.3, 0.5)),
        "nvt_ratio": float(rng.uniform(5, 200)),
        "realized_vol": float(rng.uniform(0.4, 1.2)),
        "coin_id": sym.lower() + "-mock",
        "category": random.choice(["L1", "L2", "DeFi", "Exchange"]),
    }
memory_store("features_matrix", features)
logger.info("Features injected for %d assets", len(features))

# Synthetic macro data
memory_store("macro_data", {
    "fear_greed_index": 55,
    "fear_greed_class": "Greed",
    "btc_dominance": 48.5,
    "total_market_cap_usd": 2.3e12,
    "market_cap_change_24h": 1.2,
    "dxy": 104.3,
    "fed_funds_rate": 5.25,
    "vix": 18.0,
})
logger.info("Macro data injected")

# ── 2. Run MacroAgent ────────────────────────────────────────────────────────
logger.info("\n=== MacroAgent ===")
from agents.macro_agent import MacroAgent
MacroAgent().run()
from memory.claude_flow_store import memory_retrieve
logger.info("macro_score = %.4f | regime = %s",
    memory_retrieve("macro_score"), memory_retrieve("macro_regime"))

# ── 3. Mock S1 signals (skip LLM to avoid API call) ─────────────────────────
logger.info("\n=== S1 Signals (mock — bypassing LLM) ===")
mock_buys_s1  = set(random.sample(SYMBOLS, 12))
mock_sells_s1 = set(random.sample([s for s in SYMBOLS if s not in mock_buys_s1], 4))
memory_store("s1_signals", {"buys": list(mock_buys_s1), "sells": list(mock_sells_s1)})
memory_store("s1_strengths", {s: rng.uniform(0.3, 1.0) for s in SYMBOLS})
logger.info("S1: buys=%d sells=%d", len(mock_buys_s1), len(mock_sells_s1))

# ── 4. Mock S2 signals (skip BERT/Twitter) ───────────────────────────────────
logger.info("\n=== S2 Signals (mock — bypassing sentiment APIs) ===")
mock_buys_s2  = set(random.sample(SYMBOLS, 10))
mock_sells_s2 = set(random.sample([s for s in SYMBOLS if s not in mock_buys_s2], 3))
memory_store("s2_signals", {"buys": list(mock_buys_s2), "sells": list(mock_sells_s2)})
memory_store("s2_scores", {s: float(rng.uniform(-0.5, 0.5)) for s in SYMBOLS})
logger.info("S2: buys=%d sells=%d", len(mock_buys_s2), len(mock_sells_s2))

# ── 5. ConsensusAgent ────────────────────────────────────────────────────────
logger.info("\n=== ConsensusAgent ===")
from agents.consensus_agent import ConsensusAgent
ConsensusAgent().run()
selected = memory_retrieve("selected_universe", [])
logger.info("Selected universe: %s", selected)

# ── 6. QuantAgent ────────────────────────────────────────────────────────────
logger.info("\n=== QuantAgent (15 precision × objective combos) ===")
from agents.quant_agent import QuantAgent
QuantAgent().run()
weights = memory_retrieve("optimal_weights", {})
best   = memory_retrieve("best_method", "N/A")
sharpe = memory_retrieve("all_sharpe_ratios", {})
logger.info("Best method: %s", best)
logger.info("Weights: %s", {k: round(v, 4) for k, v in weights.items()})
logger.info("Sharpe table:\n%s",
    "\n".join(f"  {k}: {v:.4f}" for k, v in
              sorted(sharpe.items(), key=lambda x: -x[1])))

# ── 7. Paper Trading: rebalance + NAV ────────────────────────────────────────
logger.info("\n=== Paper Trading: Rebalance ===")
from paper_trading.portfolio import Portfolio
from paper_trading.executor import PaperExecutor
from paper_trading.performance import PerformanceTracker

portfolio = Portfolio(db_path="/tmp/mock_portfolio.db")
executor  = PaperExecutor(portfolio)

# Build price map from mock universe (symbol → price)
price_map = {c["symbol"]: c["current_price"] for c in universe}

# Convert weight keys (coin_ids) → symbols for mock run
# QuantAgent stores by coin_id; mock IDs are <sym>-mock → strip "-mock"
sym_weights = {}
for key, w in weights.items():
    sym = key.replace("-mock", "").upper() if "-mock" in key else key.upper()
    if sym in price_map:
        sym_weights[sym] = w
if not sym_weights:
    sym_weights = {s: 1/len(selected) for s in selected if s in price_map}

executor.rebalance(sym_weights, price_map)
nav = portfolio.compute_nav(price_map)
portfolio.record_nav(nav)

# Simulate 12 months of NAV history on different dates for metrics
import datetime as dt
base_date = dt.date(2025, 5, 1)
running_nav = nav
for month in range(12):
    d = (base_date + dt.timedelta(days=30 * month)).strftime("%Y-%m-%d")
    running_nav = running_nav * (1 + float(rng.uniform(-0.08, 0.18)))
    with portfolio._conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO nav_history (date, nav) VALUES (?, ?)",
            (d, running_nav),
        )

metrics = PerformanceTracker(portfolio).compute_metrics()

logger.info("NAV after rebalance: $%.2f", nav)
logger.info("Holdings: %s", list(portfolio.get_holdings().keys()))
logger.info("Performance metrics: %s", metrics)

# ── 8. Dashboard ─────────────────────────────────────────────────────────────
logger.info("\n=== Generating Dashboard ===")
from reports.dashboard import generate_dashboard
state = portfolio.get_state()
mem_data = {
    "s1_signals": memory_retrieve("s1_signals"),
    "s2_signals": memory_retrieve("s2_signals"),
    "selected_universe": memory_retrieve("selected_universe"),
    "best_method": memory_retrieve("best_method"),
    "all_sharpe_ratios": memory_retrieve("all_sharpe_ratios"),
    "emergency_log": memory_retrieve("emergency_log", []),
}
path = generate_dashboard(state, metrics, mem_data)
logger.info("Dashboard saved: %s", path)

# ── Summary ──────────────────────────────────────────────────────────────────
logger.info("\n" + "="*60)
logger.info("MOCK DRY-RUN COMPLETE — all pipeline stages OK")
logger.info("="*60)
logger.info("Selected assets  : %d", len(selected))
logger.info("Best method      : %s", best)
logger.info("NAV              : $%.2f", nav)
logger.info("Sharpe (OOS)     : %.4f", metrics.get("sharpe_ratio", 0))
logger.info("Max Drawdown     : %.1f%%", metrics.get("max_drawdown_pct", 0))
logger.info("Dashboard        : reports/dashboard.html")
