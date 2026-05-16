"""CLI script for historical backtest of the crypto portfolio system."""

import argparse
import logging
import os
import sys

logger = logging.getLogger(__name__)


def run(env: dict = None, start_date: str = None, oos_start: str = None) -> dict:
    """Run a full historical backtest and return metrics."""
    import json
    import numpy as np
    import pandas as pd

    from config import (
        BACKTEST_START_DATE,
        PORTFOLIO_OBJECTIVES,
        PRECISION_METHODS,
        REPORTS_DIR,
        RISK_AVERSION_RHO,
        RISK_FREE_RATE,
        ROLLING_WINDOW_MONTHS,
        TARGET_PORTFOLIO_SIZE,
        TRANSACTION_COST_RATE,
    )
    from data.universe import fetch_universe
    from data.historical import build_returns_matrix
    from models.precision_matrix import PrecisionMatrixEstimator
    from models.portfolio_optimizer import PortfolioOptimizer

    env = env or {}
    api_key = env.get("COINGECKO_API_KEY")
    start = start_date or BACKTEST_START_DATE
    oos = oos_start

    logger.info("[Backtest] Fetching universe…")
    universe = fetch_universe(api_key)
    coin_ids = [c["id"] for c in universe[:TARGET_PORTFOLIO_SIZE]]

    logger.info("[Backtest] Building returns matrix…")
    R = build_returns_matrix(coin_ids, api_key, ROLLING_WINDOW_MONTHS)

    if R.empty:
        logger.error("[Backtest] No return data available")
        return {}

    # Filter by start date
    R.index = pd.to_datetime(R.index)
    R = R[R.index >= pd.Timestamp(start)]

    if oos:
        R_train = R[R.index < pd.Timestamp(oos)]
        R_oos   = R[R.index >= pd.Timestamp(oos)]
    else:
        split = int(len(R) * 0.7)
        R_train = R.iloc[:split]
        R_oos   = R.iloc[split:]

    logger.info("[Backtest] Train: %d  OOS: %d", len(R_train), len(R_oos))

    if len(R_train) < 6 or len(R_oos) < 1:
        logger.error("[Backtest] Insufficient data for train/OOS split")
        return {}

    estimator = PrecisionMatrixEstimator()
    optimizer = PortfolioOptimizer()
    mu = R_train.mean().values

    results = {}
    for method in PRECISION_METHODS:
        for objective in PORTFOLIO_OBJECTIVES:
            key = f"{method}_{objective}"
            try:
                Gamma = estimator.estimate(method, R_train)
                w = optimizer.optimize(objective, Gamma, mu, RISK_AVERSION_RHO)
                oos_returns = (R_oos.fillna(0).values @ w)
                mean_r = np.mean(oos_returns)
                std_r  = np.std(oos_returns, ddof=1)
                sharpe = (mean_r - RISK_FREE_RATE / 12) / std_r * np.sqrt(12) if std_r > 1e-12 else 0.0
                c = TRANSACTION_COST_RATE
                turnover = float(np.sum(np.abs(w - np.ones(len(w)) / len(w))))
                net_returns = oos_returns - c * (1 + oos_returns) * turnover
                mean_net = np.mean(net_returns)
                std_net  = np.std(net_returns, ddof=1)
                sharpe_net = (mean_net - RISK_FREE_RATE / 12) / std_net * np.sqrt(12) if std_net > 1e-12 else 0.0
                results[key] = {
                    "sharpe_gross": round(float(sharpe), 4),
                    "sharpe_net":   round(float(sharpe_net), 4),
                    "turnover":     round(turnover, 4),
                    "mean_return":  round(float(mean_net * 12 * 100), 4),
                }
                logger.info("[Backtest] %s  Sharpe(net)=%.4f", key, sharpe_net)
            except Exception as exc:
                logger.warning("[Backtest] %s failed: %s", key, exc)

    best = max(results, key=lambda k: results[k]["sharpe_net"]) if results else "N/A"
    print("\n" + "=" * 60)
    print("BACKTEST RESULTS")
    print("=" * 60)
    print(f"Best combination: {best}")
    if best != "N/A":
        print(f"Net Sharpe: {results[best]['sharpe_net']:.4f}")
        print(f"Ann. Return: {results[best]['mean_return']:.2f}%")
    print()
    for k, v in sorted(results.items(), key=lambda x: x[1]["sharpe_net"], reverse=True):
        print(f"  {k:<20} Sharpe(net)={v['sharpe_net']:+.4f}  Return={v['mean_return']:+.2f}%")

    os.makedirs(REPORTS_DIR, exist_ok=True)
    import json
    out_path = os.path.join(REPORTS_DIR, "backtest_results.json")
    with open(out_path, "w") as fh:
        json.dump({"results": results, "best": best}, fh, indent=2)
    logger.info("[Backtest] Results saved to %s", out_path)

    return results


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description="Historical backtest")
    parser.add_argument("--start", type=str, default=None)
    parser.add_argument("--out-of-sample-start", type=str, default=None)
    args = parser.parse_args()

    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    env = {
        "COINGECKO_API_KEY": os.environ.get("COINGECKO_API_KEY", ""),
    }
    run(env, args.start, args.out_of_sample_start)
