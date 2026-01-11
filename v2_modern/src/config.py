
# --- Application Config ---
APP_NAME = "AI Trader V12"
VERSION = "12.0"

# --- Exchange Config ---
EXCHANGE_ID = 'kraken' # 'binance', 'coinbase', 'kraken'

# --- Asset Universe ---
# Defines the assets we trade and their classification
SYMBOL_MAP = {
    'BTC/USD': 'MAJOR', 'ETH/USD': 'MAJOR', 'SOL/USD': 'MAJOR',
    'DOGE/USD': 'MEME', 'PEPE/USD': 'MEME', 'WIF/USD': 'MEME', 
    'SHIB/USD': 'MEME', 'BONK/USD': 'MEME',
    'NEAR/USD': 'ALT', 'FET/USD': 'ALT'
}
TARGET_ASSETS = list(SYMBOL_MAP.keys())

# --- Strategy Config Defaults ---
# These can be overridden by specific runners (backtest/replay)
DEFAULT_CONFIG = {
    "BASE_LEVERAGE": 5,        # Conservative Start
    "MAX_LEVERAGE": 10,        # Max cap
    "VELOCITY_THRESHOLD": 0.05, # % change per scan to trigger attention
    "VELOCITY_SLOPE_THRESHOLD": 0.01, # Acceleration required
    "MAX_SPREAD_PCT": 0.15,    # Max bid-ask spread to allow entry
    "ATR_PERIOD": 14,
    "POLL_INTERVAL": 3,        # Seconds between scans (Live)
    "ARM_PERSISTENCE": 3,      # Scans required to hold ARM state
    "ARM_TIMEOUT_SECONDS": 60, # Reset ARM if no entry after N seconds
    "COOLDOWN_MINUTES": 5,     # Minutes to wait after a loss
    "PROFIT_TARGET_PCT": 1.5,
    "STOP_LOSS_PCT": 2.0       # Hard stop
}
