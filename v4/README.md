# v4 Paper Trading Engine

A clean, production-ready paper trading pipeline supporting multiple concurrent strategies.

## Features

- **Data Layer**: CCXT-based historical and live data (REST polling). Cached to Parquet.
- **Strategies**:
  - `Momentum`: ARM (Velocity + Acceleration).
  - `Mean Reversion`: Bollinger Bands + RSI.
  - `Trend Following`: EMA Cross.
  - `Breakout`: Donchian Channels.
- **Execution**: Isolated $100 allocation per (Symbol, Strategy). Risk managed.
- **Runner**: Async parallel execution.
- **Dashboard**: Rich TUI for live monitoring.

## Setup

1. Install dependencies:
   ```bash
   pip install -r v4/requirements.txt
   ```

   ```bash
   python v4/main.py --config v4/config.yaml
   ```
   *Note: By default (mode='paper'), this connects to Binance live data.*

## Configuration

Edit `v4/config.yaml`:

```yaml
symbols:
  - BTC/USDT
strategies:
  - name: momentum
    params: { lookback: 12 }
mode: paper # or backtest
```

## Research/Experimentation
Run specific research modes:
```bash
python v4/main.py --experiment universe
python v4/main.py --experiment regime
python v4/main.py --experiment full
```

## Architecture

- `v4/data`: Feed and Provider implementations.
- `v4/engine`: Core State Machine and Position logic.
- `v4/strategies`: Strategy implementations.
- `v4/runner`: Async runner.
- `v4/dashboard`: TUI.

## Adding a Strategy

1. Create `v4/strategies/my_strategy.py`.
2. Inherit from `Strategy`.
3. Implement `generate_signals`.
4. Register in `v4/runner/runner.py` `STRATEGY_MAP`.
