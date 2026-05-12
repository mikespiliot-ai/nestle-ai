"""
Historical backtest runner.
Usage:
  python backtest_historical.py --start 2020-01 --end 2024-12 --out-of-sample-start 2023-01
"""

import argparse
import json
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", default="2020-01")
    parser.add_argument("--end", default="2024-12")
    parser.add_argument("--out-of-sample-start", default="2023-01")
    args = parser.parse_args()

    env = {k: os.environ.get(k, "") for k in [
        "ANTHROPIC_API_KEY", "COINGECKO_API_KEY", "BINANCE_API_KEY",
        "BINANCE_SECRET", "TWITTER_BEARER_TOKEN", "REDDIT_CLIENT_ID",
        "REDDIT_CLIENT_SECRET", "GLASSNODE_API_KEY", "NEWSAPI_KEY", "FRED_API_KEY",
    ]}

    if not env.get("ANTHROPIC_API_KEY"):
        logger.error("ANTHROPIC_API_KEY required")
        sys.exit(1)

    logger.info("Historical backtest: %s → %s (OOS from %s)", args.start, args.end, args.out_of_sample_start)

    from agents.data_agent import DataAgent
    from agents.crypto_signal_agent import CryptoSignalAgent
    from agents.sentiment_agent import SentimentAgent
    from agents.macro_agent import MacroAgent
    from agents.consensus_agent import ConsensusAgent
    from agents.quant_agent import QuantAgent
    from agents.backtest_agent import BacktestAgent

    logger.info("Step 1: Fetching data...")
    DataAgent(env).run()

    logger.info("Step 2: Running screening agents...")
    CryptoSignalAgent(env).run()
    SentimentAgent(env).run()
    MacroAgent().run()

    logger.info("Step 3: Consensus + optimization...")
    ConsensusAgent().run()
    QuantAgent().run()

    logger.info("Step 4: Paper trading execution...")
    ba = BacktestAgent()
    ba.run(env)

    from paper_trading.performance import PerformanceTracker
    from paper_trading.portfolio import Portfolio
    from config import PAPER_TRADING_DB

    portfolio = Portfolio(db_path=PAPER_TRADING_DB)
    perf = PerformanceTracker(portfolio)
    metrics = perf.compute_metrics()

    logger.info("=" * 50)
    logger.info("BACKTEST RESULTS")
    for k, v in metrics.items():
        logger.info("  %-35s %s", k, v)
    logger.info("=" * 50)

    with open("reports/backtest_results.json", "w") as f:
        json.dump(metrics, f, indent=2)
    logger.info("Results saved to reports/backtest_results.json")


if __name__ == "__main__":
    main()
