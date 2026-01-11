# Quick Start: Running 20 Volatile Coins in Parallel

## Option 1: Use the Parallel Runner (Recommended)

```bash
python run_volatile_20.py --start-date 2024-01-01 --end-date 2024-01-07 --max-workers 10
```

This will run all 20 volatile coins concurrently:
- **Tier 1**: BTCUSDT, ETHUSDT, BNBUSDT, SOLUSDT, ADAUSDT
- **Tier 2**: AVAXUSDT, MATICUSDT, DOTUSDT, LINKUSDT, ATOMUSDT  
- **Tier 3**: NEARUSDT, APTUSDT, ARBUSDT, OPUSDT, RUNEUSDT
- **Tier 4**: INJUSDT, SUIUSDT, SEIUSDT, TIAUSDT, PENDLEUSDT

Results saved to: `results_volatile_20/{SYMBOL}/`

## Option 2: Use historical_runner.py Directly

```bash
python historical_runner.py \
  --symbols BTCUSDT ETHUSDT BNBUSDT SOLUSDT ADAUSDT AVAXUSDT MATICUSDT DOTUSDT LINKUSDT ATOMUSDT NEARUSDT APTUSDT ARBUSDT OPUSDT RUNEUSDT INJUSDT SUIUSDT SEIUSDT TIAUSDT PENDLEUSDT \
  --start-date 2024-01-01 \
  --end-date 2024-01-07
```

**Note**: This processes symbols sequentially, not in parallel.

## Adjust Worker Count

```bash
# Low CPU: 4 workers
python run_volatile_20.py --start-date 2024-01-01 --end-date 2024-01-07 --max-workers 4

# High CPU: 20 workers (one per coin)
python run_volatile_20.py --start-date 2024-01-01 --end-date 2024-01-07 --max-workers 20
```

## Run Specific Tiers

```bash
# Tier 1 only (safer, higher liquidity)
python run_volatile_20.py \
  --symbols BTCUSDT ETHUSDT BNBUSDT SOLUSDT ADAUSDT \
  --start-date 2024-01-01 \
  --end-date 2024-01-07 \
  --max-workers 5
```

## Expected Runtime

- **Single coin (sequential)**: ~30-60 seconds
- **20 coins in parallel (10 workers)**: ~2-4 minutes
- **20 coins sequential**: ~15-20 minutes

## Output Structure

```
results_volatile_20/
├── BTCUSDT/
│   ├── historical_trades.csv
│   └── daily_summary.csv
├── ETHUSDT/
│   ├── historical_trades.csv
│   └── daily_summary.csv
...
└── PENDLEUSDT/
    ├── historical_trades.csv
    └── daily_summary.csv
```

## Analyze Combined Results

After running parallel evaluation, you can analyze individual or combined results:

```bash
# Analyze single coin
python analyze_historical.py --trades results_volatile_20/BTCUSDT/historical_trades.csv

# Combine all results (manual aggregation needed)
# TODO: Create aggregate_results.py script
```

## Troubleshooting

**Out of Memory:**
```bash
# Reduce workers
python run_volatile_20.py --start-date 2024-01-01 --end-date 2024-01-07 --max-workers 2
```

**API Rate Limiting:**
- First run will fetch and cache data
- Subsequent runs use cache automatically
- If rate limited, wait 1 minute and re-run

**Timeout Errors:**
- Default timeout: 10 minutes per symbol
- Check logs for specific symbol failures
- Re-run failed symbols individually
