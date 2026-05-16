# config.py — Central configuration for Autonomous Crypto Portfolio System

# ── Universe & Portfolio ────────────────────────────────────────────────────
CRYPTO_UNIVERSE_SIZE = 80
TARGET_PORTFOLIO_SIZE = 15

STABLECOIN_LIST = [
    "tether", "usd-coin", "binance-usd", "dai", "frax", "true-usd",
    "paxos-standard", "usdd", "gemini-dollar", "liquity-usd",
    "fei-usd", "neutrino", "terrausd", "magic-internet-money",
    "usdt", "usdc", "busd", "tusd", "usdp", "gusd", "lusd",
]

# ── Rolling Window ──────────────────────────────────────────────────────────
ROLLING_WINDOW_MONTHS = 60
MIN_HISTORY_MONTHS = 24

# ── Risk / Cost ─────────────────────────────────────────────────────────────
RISK_AVERSION_RHO = 0.01
TRANSACTION_COST_BPS = 50
TRANSACTION_COST_RATE = 0.005   # 50 bps

# ── Features ────────────────────────────────────────────────────────────────
FEATURES = ["log_mcap", "vol_to_mcap", "mom30d", "nvt_ratio", "realized_vol"]

# ── Sentiment ───────────────────────────────────────────────────────────────
SENTIMENT_BUY_THRESHOLD  =  0.10
SENTIMENT_SELL_THRESHOLD = -0.10
SENTIMENT_HALFLIFE_DAYS  =  7

# ── Sensor Intervals ────────────────────────────────────────────────────────
MACRO_SENSOR_INTERVAL_MINUTES   = 60
ONCHAIN_SENSOR_INTERVAL_MINUTES = 30
SOCIAL_SENSOR_INTERVAL_MINUTES  = 15

# ── Emergency System ────────────────────────────────────────────────────────
EMERGENCY_TRIGGER_SCORE    = 0.70
EMERGENCY_COOLDOWN_HOURS   = 48

EMERGENCY_MACRO_WEIGHT   = 0.35
EMERGENCY_ONCHAIN_WEIGHT = 0.35
EMERGENCY_SOCIAL_WEIGHT  = 0.30

EMERGENCY_DEFENSIVE_THRESHOLD = 0.90
EMERGENCY_REDUCE_THRESHOLD    = 0.75
EMERGENCY_HEDGE_THRESHOLD     = 0.70

DEFENSIVE_CASH_FRACTION   = 0.80
REDUCE_POSITION_FRACTION  = 0.40

# ── Paper Trading ───────────────────────────────────────────────────────────
INITIAL_CAPITAL_USD       = 10_000.0
PAPER_TRADING             = True
REBALANCE_DRIFT_THRESHOLD = 0.05

# ── API Endpoints ───────────────────────────────────────────────────────────
COINGECKO_BASE_URL  = "https://api.coingecko.com/api/v3"
BINANCE_BASE_URL    = "https://api.binance.com/api/v3"
GLASSNODE_BASE_URL  = "https://api.glassnode.com/v1"
FRED_BASE_URL       = "https://api.stlouisfed.org/fred/series/observations"
FEAR_GREED_URL      = "https://api.alternative.me/fng/"
NEWSAPI_BASE_URL    = "https://newsapi.org/v2"

COINGECKO_CALLS_PER_MIN = 50

# ── Onchain Thresholds ──────────────────────────────────────────────────────
EXCHANGE_INFLOW_MULTIPLIER    = 2.0
WHALE_TRANSFER_BTC_THRESHOLD  = 10_000
LIQUIDATION_ALERT_USD         = 500_000_000
STABLECOIN_SUPPLY_CHANGE_PCT  = 5.0
HASH_RATE_DROP_THRESHOLD      = 0.15

# ── Social Thresholds ───────────────────────────────────────────────────────
TWEET_VOLUME_SPIKE_MULTIPLIER = 3.0
SENTIMENT_PANIC_THRESHOLD     = -0.40
SOCIAL_PANIC_TRIGGER          = 0.75
SOCIAL_FOMO_TRIGGER           = 0.75

# ── Macro Thresholds ────────────────────────────────────────────────────────
MACRO_REDUCE_THRESHOLD    = -0.6
MACRO_DEFENSIVE_THRESHOLD = -0.8
VIX_RISK_OFF_LEVEL        = 30

MACRO_EVENT_WEIGHTS = {
    "fed_rate_hike":        -0.8,
    "fed_rate_cut":          0.6,
    "regulatory_ban":       -0.9,
    "etf_approval":          0.8,
    "exchange_hack":        -0.7,
    "stablecoin_depeg":     -0.85,
    "institutional_buy":     0.5,
    "institutional_sell":   -0.5,
    "macro_recession":      -0.7,
    "inflation_spike":      -0.4,
    "liquidity_crisis":     -0.9,
    "market_crash":         -0.8,
    "geopolitical_crisis":  -0.5,
    "default":              -0.3,
}

# ── Precision Matrix & Portfolio ────────────────────────────────────────────
PRECISION_METHODS    = ["NW", "RNW", "POET", "DL", "NLS"]
PORTFOLIO_OBJECTIVES = ["GMV", "MV", "MSR"]

PCA_FACTORS       = 3
DL_HIDDEN_LAYERS  = [256, 128, 64]
DL_DROPOUT        = 0.2
DL_TRAIN_MONTHS   = 48
DL_EVAL_MONTHS    = 12

# ── Backtest ────────────────────────────────────────────────────────────────
BACKTEST_START_DATE = "2020-01-01"
RISK_FREE_RATE      = 0.0

# ── Dashboard ───────────────────────────────────────────────────────────────
DASHBOARD_REFRESH_MINUTES = 5
REPORTS_DIR = "reports"
LOGS_DIR    = "logs"

# ── Scheduling ──────────────────────────────────────────────────────────────
MONTHLY_CYCLE_DAY  = 1
MONTHLY_CYCLE_HOUR = 0

# ── Persistence ─────────────────────────────────────────────────────────────
PAPER_TRADING_DB = "paper_trading/portfolio.db"
MEMORY_FILE      = "memory/state.json"

# ── Binance Testnet ─────────────────────────────────────────────────────────
BINANCE_TESTNET_BASE = "https://testnet.binance.vision/api/v3"
BINANCE_TESTNET_WS   = "wss://testnet.binance.vision/ws"
