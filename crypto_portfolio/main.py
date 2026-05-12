"""
MAIN ORCHESTRATOR
Runs the monthly rebalancing cycle and starts background sensor threads.
Also provides a historical backtest mode (--dry-run, --mock-data).
"""

import argparse
import logging
import os
import sys
import threading
import time
from datetime import datetime

import schedule
from dotenv import load_dotenv

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/main.log"),
    ],
)
logger = logging.getLogger(__name__)


def load_env() -> dict:
    return {
        "ANTHROPIC_API_KEY": os.environ.get("ANTHROPIC_API_KEY", ""),
        "COINGECKO_API_KEY": os.environ.get("COINGECKO_API_KEY", ""),
        "BINANCE_API_KEY": os.environ.get("BINANCE_API_KEY", ""),
        "BINANCE_SECRET": os.environ.get("BINANCE_SECRET", ""),
        "TWITTER_BEARER_TOKEN": os.environ.get("TWITTER_BEARER_TOKEN", ""),
        "REDDIT_CLIENT_ID": os.environ.get("REDDIT_CLIENT_ID", ""),
        "REDDIT_CLIENT_SECRET": os.environ.get("REDDIT_CLIENT_SECRET", ""),
        "GLASSNODE_API_KEY": os.environ.get("GLASSNODE_API_KEY", ""),
        "NEWSAPI_KEY": os.environ.get("NEWSAPI_KEY", ""),
        "FRED_API_KEY": os.environ.get("FRED_API_KEY", ""),
    }


# ── Monthly cycle ────────────────────────────────────────────────────────────

def monthly_cycle(env: dict, dry_run: bool = False):
    logger.info("=" * 60)
    logger.info("MONTHLY CYCLE STARTED: %s", datetime.utcnow().isoformat())

    from agents.data_agent import DataAgent
    from agents.crypto_signal_agent import CryptoSignalAgent
    from agents.sentiment_agent import SentimentAgent
    from agents.macro_agent import MacroAgent
    from agents.consensus_agent import ConsensusAgent
    from agents.quant_agent import QuantAgent
    from agents.backtest_agent import BacktestAgent

    # Step 1: Data (must complete first)
    DataAgent(env).run()

    # Step 2: Signal generation in parallel threads
    threads = []
    for AgentClass in [CryptoSignalAgent, SentimentAgent]:
        a = AgentClass(env)
        t = threading.Thread(target=a.run, daemon=True)
        threads.append(t)
    # Macro agent (no API key dependency beyond data)
    macro_thread = threading.Thread(target=MacroAgent().run, daemon=True)
    threads.append(macro_thread)

    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=300)

    # Step 3: Sequential consensus → quant → execute
    ConsensusAgent().run()
    QuantAgent().run()

    if not dry_run:
        BacktestAgent().run(env)

    logger.info("MONTHLY CYCLE COMPLETE: %s", datetime.utcnow().isoformat())
    logger.info("=" * 60)


# ── Sensor threads ────────────────────────────────────────────────────────────

def start_sensor_threads(env: dict, backtest_agent):
    from sensors.macro_sensor import MacroSensor
    from sensors.onchain_sensor import OnchainSensor
    from sensors.social_sensor import SocialSensor
    from sensors.risk_evaluator import RiskEvaluator

    risk_eval = RiskEvaluator(
        backtest_agent_fn=lambda action, prices: backtest_agent.run_emergency_action(action, prices)
    )

    sensors = [
        (MacroSensor(env), "MacroSensor"),
        (OnchainSensor(env), "OnchainSensor"),
        (SocialSensor(env), "SocialSensor"),
    ]

    for sensor, name in sensors:
        t = threading.Thread(
            target=sensor.start,
            args=(risk_eval.on_sensor_event,),
            name=name,
            daemon=True,
        )
        t.start()
        logger.info("Started sensor thread: %s", name)


# ── Historical backtest ───────────────────────────────────────────────────────

def run_historical_backtest(start_date: str = "2020-01-01", out_of_sample_start: str = "2023-01-01"):
    logger.info("Running historical backtest from %s (OOS from %s)", start_date, out_of_sample_start)
    env = load_env()
    # Run a single full cycle using all available historical data
    monthly_cycle(env, dry_run=False)
    logger.info("Historical backtest complete — check reports/ for output")


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Crypto Portfolio Management System")
    parser.add_argument("--dry-run", action="store_true", help="Run cycle without executing trades")
    parser.add_argument("--mock-data", action="store_true", help="Use mock data for testing")
    parser.add_argument("--backtest", action="store_true", help="Run historical backtest and exit")
    parser.add_argument("--start", default="2020-01-01", help="Backtest start date")
    parser.add_argument("--out-of-sample-start", default="2023-01-01")
    args = parser.parse_args()

    os.makedirs("logs", exist_ok=True)
    os.makedirs("reports", exist_ok=True)

    env = load_env()

    if not env.get("ANTHROPIC_API_KEY"):
        logger.error("ANTHROPIC_API_KEY not set — exiting")
        sys.exit(1)

    if args.backtest:
        run_historical_backtest(args.start, args.out_of_sample_start)
        return

    # Run one immediate cycle at startup
    monthly_cycle(env, dry_run=args.dry_run)

    if args.dry_run:
        logger.info("Dry-run complete — exiting")
        return

    # Start background sensors
    from agents.backtest_agent import BacktestAgent
    ba = BacktestAgent()
    start_sensor_threads(env, ba)

    # Schedule monthly on 1st of each month at 00:00 UTC
    schedule.every().month.do(monthly_cycle, env=env)

    logger.info("Scheduler running — waiting for next monthly cycle (Ctrl+C to stop)")
    while True:
        schedule.run_pending()
        time.sleep(60)


if __name__ == "__main__":
    main()
