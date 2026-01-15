# AI Trader v4.0

A modular, production-grade crypto trading engine with pluggable strategies, robust risk management, and advanced backtesting capabilities.

## Key Features
- **Pluggable Strategies**: Momentum, Mean Reversion, Trend Following, Breakout, Scalping.
- **Robust Risk Management**: Centralized position sizing, risk limits, and loser suppression.
- **Advanced Backtesting**: Supports fees, slippage simulation, and In-Sample/Out-of-Sample splitting.
- **Event-Driven**: Generic State Machine handles lifecycle (WAIT -> ENTRY -> HOLD -> EXIT).

## Setup
1. Install dependencies (standard requirements + `rich`, `pandas`, `ccxt`, `ta-lib` if needed).
2. Configure your API keys (for live modes) or ensure historical data is in `data/` folder.

## Configuration
All settings are in `engine/config.py`.
To change the active strategy, edit `active_strategy` in `DefaultConfig` or pass a custom config.

Available Strategies:
- `momentum`: Velocity-based.
- `mean_reversion`: RSI + Bollinger Bands.
- `trend_follow`: EMA Crossover.
- `breakout`: Range breakout.
- `scalping`: High-frequency velocity bursts.

## Usage

### 1. Backtesting (Historical Evaluation)
Run the `backtest.py` script.

**Basic Run:**
```bash
python v3/backtest.py --symbols BTCUSDT --start 2024-01-01 --end 2024-02-01
```

**Multi-Symbol:**
```bash
python v3/backtest.py --symbols BTCUSDT ETHUSDT --start 2024-01-01 --end 2024-01-07
```

**(Legacy) Historical Runner:**
```bash
python v3/historical_runner.py --symbol BTCUSDT --start-date 2024-01-01 --end-date 2024-06-01
```

### 2. Strategy Development
To add a new strategy:
1. Create `engine/strategies/my_strategy.py`.
2. Inherit from `Strategy` class.
3. Implement `on_tick(self, tick: Tick) -> Optional[Signal]`.
4. Export it in `engine/strategies/__init__.py`.
5. Register it in `engine/engine.py` `STRATEGY_MAP`.

### 3. Live Trading (Mock/Paper)
Use the `live_mock.py` script to run strategies against live Binance data:

```bash
# Run for specific symbols
python v3/live_mock.py --symbols BTCUSDT ETHUSDT SOLUSDT

# Run with custom parameters
python v3/live_mock.py --symbols BTCUSDT --arm-velocity 0.005 --atr-stop 2.0
```

## Architecture
See [ARCHITECTURE.md](ARCHITECTURE.md) for details on the internal components and data flow.
