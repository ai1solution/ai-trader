# AI Trader V2 (Modern)

A modernized version of the trading engine with a structured runner system supporting Live, Replay, and Backtest modes.

## Usage

The entry point is `v2_modern/main.py`.

### 1. View Help
```bash
python v2_modern/main.py --help
```

### 2. Run Backtest
```bash
# Example
python v2_modern/main.py backtest --symbol BTC/USDT --days 7
```
*(Check `python v2_modern/main.py backtest --help` for all options)*

### 3. Run Live Trading
```bash
python v2_modern/main.py live
```

### 4. Run Replay
```bash
python v2_modern/main.py replay
```

## Structure
- `src/`: Core logic (Engine, Strategy, etc.)
- `data/`: Data storage
- `logs/`: Application logs
