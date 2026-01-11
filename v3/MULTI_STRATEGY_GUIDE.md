# Multi-Strategy Live Trading - Quick Reference

## Overview

Runs **4 different risk-based strategies** simultaneously across **20-30 coins**, displaying real-time comparison in a comprehensive table.

## Strategies

| Strategy | Risk Level | Position Size | Stops | Partial Threshold | Entry Ease |
|----------|-----------|---------------|-------|-------------------|------------|
| **CONSERVATIVE** | Low | $500 | Tight (1.5%) | Low (0.35%) | Hard |
| **MODERATE** | Medium | $1000 | Normal (2%) | Medium (0.45%) | Normal |
| **AGGRESSIVE** | High | $1500 | Wide (2.5%) | High (0.55%) | Easy |
| **VERY_AGGRESSIVE** | Very High | $2000 | Widest (3%) | Highest (0.6%) | Very Easy |

## Commands

### Run 20 Coins (Default):
```bash
python live_multi_strategy.py
```

### Run 30 Coins:
```bash
python live_multi_strategy.py --coins 30
```

### Run 10 Coins (Faster):
```bash
python live_multi_strategy.py --coins 10
```

### Run for 5 Minutes:
```bash
python live_multi_strategy.py --duration 300
```

## Output Format

The table shows **per-symbol AND per-strategy metrics**:

```
Symbol    | CONSERVATIVE      | MODERATE         | AGGRESSIVE       | VERY_AGGRESSIVE
          | Trades PnL  Win%  | Trades PnL Win%  | Trades PnL Win%  | Trades PnL  Win%
----------|-------------------|------------------|------------------|------------------
BTCUSDT   |   2   $+5.20  50% |   3   $+8.40 67% |   5  $+12.30 60% |   7  $+15.80 57%
ETHUSDT   |   1   $-2.10  0%  |   2   $+3.20 50% |   4   $+9.10 75% |   6  $+14.20 67%
...
TOTAL     |  25  $+45.30  56% |  42  $+78.20 62% |  68 $+125.40 65% |  89 $+168.50 64%
```

## Key Features

1. **Comparative Analysis**: See which strategy performs best in real-time
2. **Risk vs Reward**: Compare conservative vs aggressive approaches
3. **Per-Symbol Insights**: Identify which coins work best with which strategy
4. **Live Updates**: Table refreshes every 2 seconds
5. **Parallel Execution**: All 80-120 engines (4 strategies × 20-30 coins) run simultaneously

## Total Engines Running

- 10 coins: 40 engines (4 strategies × 10 coins)
- 20 coins: 80 engines (4 strategies × 20 coins)
- 30 coins: 120 engines (4 strategies × 30 coins)

## Use Cases

**Find Optimal Strategy:**
- See which risk level yields best overall returns
- Identify strategy-coin combinations that work best

**Portfolio Optimization:**
- Balance conservative and aggressive positions
- Risk-adjusted returns comparison

**Market Condition Analysis:**
- Which strategies work in current market regime
- Trending vs ranging performance

## Logs

Individual logs per strategy-symbol combination:
- `logs/CONSERVATIVE_BTCUSDT.log`
- `logs/MODERATE_BTCUSDT.log`
- `logs/AGGRESSIVE_BTCUSDT.log`
- `logs/VERY_AGGRESSIVE_BTCUSDT.log`

## Stop

Press `Ctrl+C` to stop all engines and view final summary.

## Expected Performance

Based on v3.2 improvements, expect:
- CONSERVATIVE: Lower drawdown, moderate returns
- MODERATE: Balanced risk-reward
- AGGRESSIVE: Higher returns, higher drawdown
- VERY_AGGRESSIVE: Maximum returns, maximum risk

The **best strategy** depends on market conditions and will be highlighted in the final summary! 🏆
