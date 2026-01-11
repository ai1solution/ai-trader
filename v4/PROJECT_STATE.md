# v4 Project State & Technical Documentation

**Last Updated**: 2026-01-11
**Version**: v4.0.1 (Stable - Windows Fixes Applied)

## 1. Technical Architecture

### Core Stack
- **Language**: Python 3.10+
- **Concurrency**: `asyncio` (Single-threaded event loop) with Windows-specific Proactor fixes.
- **Data Source**: `ccxt` (REST/Async) - Binance.
- **Data Storage**: 
    - Trades: `results/trades.csv` (CSV Append-only)
    - Logs: `logs/v4_session_[timestamp].log` (File logging enabled)
- **UI**: `rich` (Terminal User Interface)

### Module Structure
| Module | Responsibility | Key Classes |
|--------|----------------|-------------|
| `v4.data` | Data fetching, caching, and feed simulation | `CCXTProvider`, `HistoricalFeed`, `LiveFeed` |
| `v4.engine` | Execution logic, PnL tracking, State Machine | `TradingEngine`, `Position` |
| `v4.strategies` | Signal generation logic (Pure functions) | `Strategy` (ABC), `Importance`, `Intent` |
| `v4.runner` | Orchestrating concurrent engines | `ParallelRunner` |
| `v4.config` | Configuration schema and loading | `RunnerConfig`, `StrategyConfig` |

## 2. Trading Configuration & Strategy Profiles

The system uses a two-tier configuration approach to allow for rapid iteration and optimization by LLMs or genetic algorithms.

### A. Profiles Library (`v4/config/profiles.yaml`)
This file acts as a **registry of optimized parameter sets**. It defines different "personalities" for each strategy, allowing us to switch behavior without rewriting code.

**Typical Profiles:**
1.  **Momentum Aggressive**:
    - *Goal*: Catch early breakouts.
    - *Params*: Short lookback (8), Low threshold (0.01%), Fast persistence (2 ticks).
    - *Risk*: Higher whip-saw potential.
2.  **Momentum Standard** (Default):
    - *Goal*: Balanced trend catching.
    - *Params*: Medium lookback (12), Standard threshold (0.03%), Medium persistence (3 ticks).
3.  **Mean Reversion Tight**:
    - *Goal*: Scalp small deviations.
    - *Params*: Narrow Bands (1.5 std), Short RSI (14).
4.  **Mean Reversion Wide**:
    - *Goal*: Fade extreme moves.
    - *Params*: Wide Bands (2.5 std).

### B. Runtime Configuration (`v4/config.yaml`)
This is the **active execution file**. It selects specific strategies and parameters (often copied from a Profile) to run for the current session.

**Current Live Config:**
- **Mode**: `paper` (Live Polling, no real money).
- **Universe**: ~20 Crypto Assets (Major: BTC/ETH/SOL, AI: FET/WLD/RNDR, Meme: PEPE/WIF/BONK).
- **Active Strategies**:
    1.  `momentum` (Standard params): Catches velocity bursts.
    2.  `mean_reversion` (Standard params): Fades Bollinger Band extensions with RSI confirmation.

## 3. Trading & Execution Logic

### Execution Engine State Machine
The engine manages the lifecycle of a trade using a strict state machine:
1.  **WAIT**: Idle state. Analyzing ticks.
2.  **ENTRY**: Signal triggered.
    - **Live/Paper**: Assumes immediate fill at current price +/- 0.1% slippage.
    - **Position**: Sizing is currently ~100% of allocated capital per bot ($100 virtual).
3.  **HOLD**: Managing open position.
    - **Valuation**: Tracks High/Low watermarks for Trailing Stops.
    - **Exits**: Checks logic on *every tick*.
4.  **EXIT**: Triggered by Stop Loss, Take Profit, or Signal Reversal.
5.  **COOLDOWN**: 10s pause to prevent signal flickering.

### Strategy Implementations

#### Momentum (Velocity-Based)
*Logic*: `Velocity > Threshold` AND `Acceleration > 0`
- **Velocity**: Rate of Change (ROC) over `momentum_lookback` ticks.
- **Acceleration**: Checks if recent median velocity > older median velocity.
- **Filters**: RSI must not be overbought (for Longs) or oversold (for Shorts) to prevent buying tops.

#### Mean Reversion (Bollinger + RSI)
*Logic*: `Price < LowerBand` AND `RSI < Oversold` (Buy)
- **Bollinger Bands**: 20-period SMA +/- 2.0 StdDev.
- **RSI**: 14-period Relative Strength Index.
- **Context**: Often effective in ranging markets or high-volatility chop.

## 4. Recent Architecture Improvements (Jan 11, 2026)
- **Windows Compatibility**: Added a robust monkey-patch to `v4/main.py` to suppress `asyncio` & `SSLProtocol` shutdown errors common on Windows.
- **Logging**: Implemented persistent session logging (`logs/v4_session_*.log`) to capture run data even if the TUI is closed.
- **Graceful Shutdown**: Updated `runner.py` cleanup to allow transport closures.

## 5. Future Roadmap for LLM Optimization
- **Feedback Loop**: Use `results/trades.csv` PnL data.
- **Optimization**: AI Agents can generate new `profiles.yaml` entries based on performance.
- **Selection**: `config.yaml` can be dynamically updated to pick the "Profile of the Day".
