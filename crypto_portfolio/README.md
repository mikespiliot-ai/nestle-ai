# Crypto Portfolio Management System (Paper Trading)

Autonomous multi-agent crypto portfolio management system based on the methodology from **Caner, Capponi, Sun & Tan (2026)** "Designing Agentic AI-Based Screening for Portfolio Investment" (arXiv:2603.23300), adapted for cryptocurrency markets with event-driven emergency response.

> **Paper trading only — no real funds are ever at risk.**

## Architecture

```
3-Layer Academic Methodology
├── Layer 1: Dual screening (LLM-S + CryptoBERT Sentiment)
├── Layer 2: Consensus agent (intersection rule)
└── Layer 3: Precision matrix × portfolio objective optimization (15 combos)

Event-Driven Emergency System
├── Macro Sensor    (60-min polling)
├── Onchain Sensor  (30-min polling)
├── Social Sensor   (15-min polling)
└── Risk Evaluator  (event-driven composite scoring)
```

## Setup

### 1. Install dependencies

```bash
pip install anthropic requests pandas numpy scipy scikit-learn torch \
    transformers pycoingecko python-binance tweepy praw schedule \
    python-dotenv aiohttp matplotlib seaborn pytrends
```

### 2. Configure API keys

```bash
cp .env.example .env
# Edit .env and fill in your API keys
```

Required: `ANTHROPIC_API_KEY`  
Optional but recommended: all others (system degrades gracefully without them)

### 3. Run

```bash
# Full monthly cycle (one-shot)
python main.py

# Historical backtest (2020–2024)
python main.py --backtest --start 2020-01 --out-of-sample-start 2023-01

# Dry-run (no trade execution)
python main.py --dry-run

# Live mode with scheduler + sensors
python main.py
```

## Project Structure

```
crypto_portfolio/
├── main.py                    # Entry point, scheduler, orchestrator
├── config.py                  # All constants and thresholds
├── agents/
│   ├── data_agent.py          # Universe + features + macro data
│   ├── crypto_signal_agent.py # LLM-S screening (Layer 1a)
│   ├── sentiment_agent.py     # CryptoBERT sentiment (Layer 1b)
│   ├── macro_agent.py         # Global macro scoring
│   ├── consensus_agent.py     # Intersection rule (Layer 2)
│   ├── quant_agent.py         # Precision matrix + optimization (Layer 3)
│   └── backtest_agent.py      # Paper trading execution + metrics
├── sensors/
│   ├── macro_sensor.py        # Macro event monitoring
│   ├── onchain_sensor.py      # On-chain metrics monitoring
│   ├── social_sensor.py       # Social media panic/FOMO detection
│   └── risk_evaluator.py      # Composite emergency scoring
├── models/
│   ├── precision_matrix.py    # NW, RNW, POET, DL, NLS
│   ├── portfolio_optimizer.py # GMV, MV, MSR
│   └── cryptobert.py          # CryptoBERT wrapper
├── data/
│   ├── universe.py            # Top-80 crypto universe management
│   ├── historical.py          # Historical OHLCV + caching
│   └── live.py                # Live prices + Fear&Greed
├── paper_trading/
│   ├── portfolio.py           # SQLite-backed virtual portfolio
│   ├── executor.py            # Simulated trade execution
│   └── performance.py         # Sharpe, drawdown, Calmar metrics
├── memory/
│   └── claude_flow_store.py   # JSON-backed key-value memory store
├── reports/
│   ├── dashboard.py           # HTML dashboard generator
│   └── dashboard.html         # Live dashboard (auto-generated)
├── logs/                      # Execution + emergency logs
└── .env.example               # API key template
```

## Methodology

### Layer 1: Dual Screening
- **CryptoSignal Agent**: Sends standardized z-scored fundamentals (log_mcap, vol_to_mcap, mom30d, nvt_ratio, realized_vol) to Claude — no price levels or USD values to avoid anchoring bias
- **Sentiment Agent**: ElKulako/cryptobert applied to Twitter, Reddit, NewsAPI with exponential decay weighting (half-life = 7 days)

### Layer 2: Consensus
Exact paper formula: use intersection if |intersection| > 1, else union. Remove conflicts. Apply macro overlay to tighten buy list in risk-off environments.

### Layer 3: Portfolio Optimization
5 precision matrix methods × 3 objectives = **15 combinations**, winner selected by out-of-sample Sharpe ratio (last 12 months):

| Precision Methods | Portfolio Objectives |
|---|---|
| Nodewise Regression (NW) | Global Min Variance (GMV) |
| Residual Nodewise (RNW) | Mean-Variance (MV, ρ=0.01/month) |
| POET | Max Sharpe Ratio (MSR) |
| Deep Learning (DL) | |
| Nonlinear Shrinkage (NLS) | |

### Emergency Response
Composite score = 0.35×macro + 0.35×onchain + 0.30×social  
- Score > 0.90 → **DEFENSIVE** (move to 80% cash)  
- Score > 0.75 → **REDUCE** (cut all positions 40%)  
- Score > 0.70 → **HEDGE** (reduce highest-beta positions)  
- 48-hour cooldown between emergency rebalances

## Anti-Bias Rules (from paper)
- No returns data sent to CryptoSignal Agent — only z-scored fundamentals
- Causal masking: at time T, only data available at T is used
- Rolling 60-month window for precision matrix estimation
- Dead/delisted coins included in historical universe
- Transaction costs always applied (50bps)

## Expected Performance (backtest 2020–2024)
| Metric | Expected Range |
|---|---|
| Annualized Return | ~45–60% |
| Annualized Volatility | ~55–70% |
| Sharpe Ratio | ~0.8–1.2 |
| Max Drawdown | ~-45% to -60% |

*Not a guarantee — crypto markets are highly volatile.*
