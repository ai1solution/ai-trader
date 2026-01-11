# Historical Backtest Runner

This module (`historical_backtest_runner.py`) allows you to validate the Engine V11 logic against historical market data without risking capital or affecting the live system.

## Features
- **Offline Simulation**: Runs completely separately from the live engine (`trading_engine.py`).
- **Logic Replication**: Uses an `EngineAdapter` that mirrors the exact state machine and risk logic of V11.
- **CCXT Integration**: Fetches OHLCV data directly from Kraken (uses `1m` timeframe).
- **Metric Generation**: Outputs Win Rate, PnL, Max Drawdown, and Regime Stats.

## Usage

1. **Configure Date Range**:
   Open `historical_backtest_runner.py` and adjust the configuration at the top:
   ```python
   # Defaults to recent 24h window due to public API limits
   START_DATE_STR = "2025-12-28 10:00:00"
   END_DATE_STR   = "2025-12-28 22:00:00"
   ```
   > **Note**: Kraken's public API `fetch_ohlcv` often provides only the most recent ~720-1000 candles regardless of the requested start date. For deep history (months/years), you may need an archival data source or a paid API key with historical access.

2. **Run the Script**:
   ```bash
   python historical_backtest_runner.py
   ```

3. **Check Outputs**:
   - Console: Prints progress and Efficiency Metrics.
   - `historical_trades.csv`: Detailed log of every simulated trade.
   - `historical_summary.csv`: High-level session summary.

## How to Trust These Results

This backtester is designed for **Logic Validation**, not just PnL optimization.

### ✅ What it Validates
- **Entry Logic**: Does the engine enter where expected (velocity spikes + trend)?
- **Exit Logic**: Do simulated stops/ratchets trigger correctly?
- **Regime Detection**: Is the engine correctly identifying CHOP vs TRENDING?
- **Idle Behavior**: Does it stay out of the market during CHOP (look for `Trades Skipped (CHOP)` count)?

### ⚠️ Limitations (Why results differ from Live)
- **Data Granularity**: Simulates on **1-minute** Close prices. The live engine polls every **2 seconds**. This means simulated entries/exits are less precise (no intra-minute volatility/wicks).
- **Spread & Slippage**: The backtester assumes a fixed small spread. Live trading has variable spread and slippage.
- **Latency**: Simulation has 0ms latency. Live execution has API lag.
- **Look-Ahead Bias**: Prevented by "Chunking", but 1-minute granularity implies we know the "Close" at the end of the minute. Real engine reacts tick-by-tick.

### Interpretation
- If the backtester loses money in **CHOP**, the live engine likely will too.
- If the backtester makes money in **TRENDING**, verify if the entry prices are realistic (check `entry_quality`).
- Use `Regime Dist` to understand the market context of the test window.
