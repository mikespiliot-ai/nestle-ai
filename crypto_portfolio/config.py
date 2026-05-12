"""
Global configuration constants for the Crypto Portfolio Management System.
Based on Caner, Capponi, Sun & Tan (2026) adapted for cryptocurrency markets.
"""

# ─── Universe ─────────────────────────────────────────────────────────────────
CRYPTO_UNIVERSE_SIZE = 80
EXCLUDE_STABLECOINS = True
TARGET_PORTFOLIO_SIZE = 15
STABLECOIN_LIST = [
    "USDT", "USDC", "BUSD", "DAI", "TUSD", "USDP", "GUSD", "FRAX",
    "USDD", "LUSD", "CRVUSD", "PYUSD", "FDUSD"
]

# ─── Rolling window ────────────────────────────────────────────────────────────
ROLLING_WINDOW_MONTHS = 60
MIN_HISTORY_MONTHS = 24

# ─── Portfolio objectives ──────────────────────────────────────────────────────
RISK_AVERSION_RHO = 0.01  # Monthly risk aversion parameter

# ─── Transaction costs ────────────────────────────────────────────────────────
TRANSACTION_COST_BPS = 50  # 50 basis points (higher than equities)
TRANSACTION_COST_RATE = TRANSACTION_COST_BPS / 10000.0

# ─── LLM-S Features ───────────────────────────────────────────────────────────
FEATURES = ["log_mcap", "vol_to_mcap", "mom30d", "nvt_ratio", "realized_vol"]

# ─── Sentiment thresholds (FinBERT / CryptoBERT) ─────────────────────────────
SENTIMENT_BUY_THRESHOLD = 0.10
SENTIMENT_SELL_THRESHOLD = -0.10
SENTIMENT_HALFLIFE_DAYS = 7  # Exponential decay half-life

# ─── Sensor polling intervals ─────────────────────────────────────────────────
MACRO_SENSOR_INTERVAL_MINUTES = 60
ONCHAIN_SENSOR_INTERVAL_MINUTES = 30
SOCIAL_SENSOR_INTERVAL_MINUTES = 15

# ─── Emergency rebalancing thresholds ─────────────────────────────────────────
EMERGENCY_TRIGGER_SCORE = 0.70
EMERGENCY_COOLDOWN_HOURS = 48

# Emergency composite weights
EMERGENCY_MACRO_WEIGHT = 0.35
EMERGENCY_ONCHAIN_WEIGHT = 0.35
EMERGENCY_SOCIAL_WEIGHT = 0.30

# Emergency action thresholds
EMERGENCY_DEFENSIVE_THRESHOLD = 0.90   # Move to 80% cash
EMERGENCY_REDUCE_THRESHOLD = 0.75      # Cut all positions 40%
EMERGENCY_HEDGE_THRESHOLD = 0.70       # Reduce highest-beta positions

# Defensive mode cash allocation
DEFENSIVE_CASH_FRACTION = 0.80
REDUCE_POSITION_FRACTION = 0.40

# ─── Paper trading ────────────────────────────────────────────────────────────
INITIAL_CAPITAL_USD = 10_000.0
PAPER_TRADING = True
REBALANCE_DRIFT_THRESHOLD = 0.05  # Only rebalance if drift > 5%

# ─── Data sources ─────────────────────────────────────────────────────────────
COINGECKO_BASE_URL = "https://api.coingecko.com/api/v3"
BINANCE_BASE_URL = "https://api.binance.com/api/v3"
GLASSNODE_BASE_URL = "https://api.glassnode.com/v1"
FRED_BASE_URL = "https://api.stlouisfed.org/fred"
FEAR_GREED_URL = "https://api.alternative.me/fng/"
NEWSAPI_BASE_URL = "https://newsapi.org/v2"

# CoinGecko rate limit (free tier)
COINGECKO_CALLS_PER_MIN = 50

# ─── Onchain alert thresholds ─────────────────────────────────────────────────
EXCHANGE_INFLOW_MULTIPLIER = 2.0       # Alert if 24h inflow > 2x 30d avg
WHALE_TRANSFER_BTC_THRESHOLD = 10_000
LIQUIDATION_ALERT_USD = 500_000_000    # $500M in 1 hour
STABLECOIN_SUPPLY_CHANGE_PCT = 5.0     # 5% change in 24h
HASH_RATE_DROP_THRESHOLD = 0.15        # 15% 7-day drop

# ─── Social alert thresholds ──────────────────────────────────────────────────
TWEET_VOLUME_SPIKE_MULTIPLIER = 3.0    # 3x 24h average in 1 hour
SENTIMENT_PANIC_THRESHOLD = -0.40      # CryptoBERT avg < -0.4 → alert
SOCIAL_PANIC_TRIGGER = 0.75
SOCIAL_FOMO_TRIGGER = 0.75

# ─── Macro scoring thresholds ─────────────────────────────────────────────────
MACRO_REDUCE_THRESHOLD = -0.6
MACRO_DEFENSIVE_THRESHOLD = -0.8
MACRO_REDUCE_FRACTION = 0.30
VIX_RISK_OFF_LEVEL = 30

# Macro event weights
MACRO_EVENT_WEIGHTS = {
    "fed_rate_hike_unexpected": -0.8,
    "fed_rate_cut": 0.5,
    "exchange_hack_large": -0.9,
    "stablecoin_depeg": -0.95,
    "country_bans_crypto": -0.6,
    "country_legalizes_crypto": 0.4,
    "regulatory_clarity": 0.3,
    "geopolitical_escalation": -0.4,
}

# ─── Precision matrix methods ─────────────────────────────────────────────────
PRECISION_METHODS = ["NW", "RNW", "POET", "DL", "NLS"]
PORTFOLIO_OBJECTIVES = ["GMV", "MV", "MSR"]
PCA_FACTORS = 3

# Deep Learning precision matrix architecture
DL_HIDDEN_LAYERS = [256, 128, 64]
DL_DROPOUT = 0.2
DL_TRAIN_MONTHS = 48
DL_EVAL_MONTHS = 12

# ─── Backtest ─────────────────────────────────────────────────────────────────
BACKTEST_START_DATE = "2020-01-01"
OUT_OF_SAMPLE_START = "2023-01-01"
RISK_FREE_RATE = 0.0  # Use 0 for crypto (no true risk-free equivalent)

# ─── Reporting ────────────────────────────────────────────────────────────────
DASHBOARD_REFRESH_MINUTES = 5
REPORTS_DIR = "reports"
LOGS_DIR = "logs"

# ─── Scheduler ────────────────────────────────────────────────────────────────
MONTHLY_CYCLE_DAY = 1   # 1st of each month
MONTHLY_CYCLE_HOUR = 0  # 00:00 UTC

# ─── Paths ────────────────────────────────────────────────────────────────────
PAPER_TRADING_DB = "paper_trading/portfolio.db"
MEMORY_FILE = "memory/state.json"
