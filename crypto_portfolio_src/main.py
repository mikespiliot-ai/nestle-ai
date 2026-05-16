"""Main orchestrator for the Autonomous Crypto Portfolio Management System."""

import argparse
import logging
import os
import sys
import threading
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import schedule

from config import (
    LOGS_DIR,
    MONTHLY_CYCLE_DAY,
    MONTHLY_CYCLE_HOUR,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(os.path.join(LOGS_DIR, "portfolio.log"), mode="a"),
    ],
)
logger = logging.getLogger(__name__)

os.makedirs(LOGS_DIR, exist_ok=True)


# ── Environment loading ────────────────────────────────────────────────────────

def load_env() -> Dict[str, Any]:
    """Load all environment variables for the system."""
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    return {
        "ANTHROPIC_API_KEY":       os.environ.get("ANTHROPIC_API_KEY", ""),
        "COINGECKO_API_KEY":       os.environ.get("COINGECKO_API_KEY", ""),
        "NEWSAPI_KEY":             os.environ.get("NEWSAPI_KEY", ""),
        "TWITTER_BEARER_TOKEN":    os.environ.get("TWITTER_BEARER_TOKEN", ""),
        "REDDIT_CLIENT_ID":        os.environ.get("REDDIT_CLIENT_ID", ""),
        "REDDIT_CLIENT_SECRET":    os.environ.get("REDDIT_CLIENT_SECRET", ""),
        "GLASSNODE_API_KEY":       os.environ.get("GLASSNODE_API_KEY", ""),
        "FRED_API_KEY":            os.environ.get("FRED_API_KEY", ""),
        "BINANCE_TESTNET_API_KEY": os.environ.get("BINANCE_TESTNET_API_KEY", ""),
        "BINANCE_TESTNET_SECRET":  os.environ.get("BINANCE_TESTNET_SECRET", ""),
    }


# ── Monthly cycle ─────────────────────────────────────────────────────────────

def monthly_cycle(env: Dict[str, Any], dry_run: bool = False) -> None:
    """Run the full monthly pipeline."""
    logger.info("=" * 60)
    logger.info("MONTHLY CYCLE STARTED  dry_run=%s", dry_run)
    logger.info("=" * 60)

    from agents.data_agent import DataAgent
    from agents.crypto_signal_agent import CryptoSignalAgent
    from agents.sentiment_agent import SentimentAgent
    from agents.macro_agent import MacroAgent
    from agents.consensus_agent import ConsensusAgent
    from agents.quant_agent import QuantAgent
    from agents.backtest_agent import BacktestAgent

    # Phase 1: Data (sequential — all others depend on it)
    DataAgent(env).run()

    # Phase 2: Signal agents (can run in parallel)
    threads = []
    for AgentClass in (CryptoSignalAgent, SentimentAgent, MacroAgent):
        t = threading.Thread(target=AgentClass(env).run, daemon=True)
        threads.append(t)
        t.start()
    for t in threads:
        t.join(timeout=300)

    # Phase 3: Sequential — consensus → quant → backtest
    ConsensusAgent(env).run()
    QuantAgent(env).run()

    if not dry_run:
        BacktestAgent(env).run(env)
    else:
        logger.info("[main] Dry-run: skipping BacktestAgent execution")

    # Generate dashboard
    from memory.claude_flow_store import memory_retrieve
    from reports.dashboard import generate_dashboard
    from paper_trading.portfolio import Portfolio
    from config import PAPER_TRADING_DB

    portfolio = Portfolio(PAPER_TRADING_DB)
    price_map = {c["id"]: c.get("current_price", 1.0)
                 for c in memory_retrieve("universe", [])}
    state = portfolio.get_state()
    metrics = memory_retrieve("performance_metrics", {})
    mem_data = {
        "nav_history":       portfolio.get_nav_history(200),
        "all_sharpe_ratios": memory_retrieve("all_sharpe_ratios", {}),
        "consensus_buys":    memory_retrieve("consensus_buys", []),
        "consensus_sells":   memory_retrieve("consensus_sells", []),
        "best_method":       memory_retrieve("best_method", "N/A"),
        "macro_regime":      memory_retrieve("macro_regime", "NORMAL"),
        "macro_score":       memory_retrieve("macro_score", 0.0),
        "alert_log":         [],
    }
    dash_path = generate_dashboard(state, metrics, mem_data)
    logger.info("Dashboard generated: %s", dash_path)
    logger.info("MONTHLY CYCLE COMPLETE")


# ── Sensor threads ────────────────────────────────────────────────────────────

def start_sensor_threads(env: Dict[str, Any], backtest_agent: Any) -> None:
    from sensors.macro_sensor import MacroSensor
    from sensors.onchain_sensor import OnchainSensor
    from sensors.social_sensor import SocialSensor
    from sensors.risk_evaluator import RiskEvaluator

    evaluator = RiskEvaluator(lambda: backtest_agent)

    macro_s   = MacroSensor(env,    evaluator.on_sensor_event)
    onchain_s = OnchainSensor(env,  evaluator.on_sensor_event)
    social_s  = SocialSensor(env,   evaluator.on_sensor_event)

    macro_s.start()
    onchain_s.start()
    social_s.start()

    logger.info("[main] All sensor threads started")
    return evaluator


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Autonomous Crypto Portfolio Manager")
    parser.add_argument("--dry-run", action="store_true", help="Skip actual trading")
    parser.add_argument("--backtest", action="store_true", help="Run historical backtest")
    parser.add_argument("--start", type=str, default=None, help="Backtest start date YYYY-MM-DD")
    parser.add_argument("--out-of-sample-start", type=str, default=None,
                        help="OOS split date YYYY-MM-DD")
    args = parser.parse_args()

    env = load_env()

    if args.backtest:
        logger.info("Running historical backtest mode")
        import backtest_historical
        backtest_historical.run(env, start_date=args.start, oos_start=args.out_of_sample_start)
        return

    logger.info("Starting Autonomous Crypto Portfolio System")

    from agents.backtest_agent import BacktestAgent
    backtest_agent = BacktestAgent(env)

    # Start background sensors
    start_sensor_threads(env, backtest_agent)

    # Run once immediately on startup
    monthly_cycle(env, dry_run=args.dry_run)

    # Schedule monthly on 1st of each month at midnight
    schedule.every().day.at(f"{MONTHLY_CYCLE_HOUR:02d}:00").do(
        lambda: _run_if_first_of_month(env, args.dry_run)
    )

    logger.info("[main] Scheduler running. Press Ctrl+C to stop.")
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)
    except KeyboardInterrupt:
        logger.info("[main] Shutting down…")


def _run_if_first_of_month(env: Dict, dry_run: bool) -> None:
    if datetime.now(timezone.utc).day == MONTHLY_CYCLE_DAY:
        monthly_cycle(env, dry_run=dry_run)


if __name__ == "__main__":
    main()
