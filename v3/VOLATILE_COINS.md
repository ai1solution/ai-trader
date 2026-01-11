# Top 20 Volatile Cryptocurrency Pairs for Trading Analysis

## High Volatility Pairs (Binance USDT)

These pairs are selected for high volatility, liquidity, and trending behavior:

### Tier 1: Large Cap Volatile (High Liquidity)
1. **BTCUSDT** - Bitcoin (benchmark)
2. **ETHUSDT** - Ethereum (major alt)
3. **BNBUSDT** - Binance Coin (exchange token)
4. **SOLUSDT** - Solana (high beta)
5. **ADAUSDT** - Cardano (momentum)

### Tier 2: Mid Cap High Beta
6. **AVAXUSDT** - Avalanche
7. **MATICUSDT** - Polygon
8. **DOTUSDT** - Polkadot
9. **LINKUSDT** - Chainlink
10. **ATOMUSDT** - Cosmos

### Tier 3: High Volatility Alts
11. **NEARUSDT** - Near Protocol
12. **APTUSDT** - Aptos
13. **ARBUSDT** - Arbitrum
14. **OPUSDT** - Optimism
15. **RUNEUSDT** - THORChain

### Tier 4: Emerging High Beta
16. **INJUSDT** - Injective
17. **SUIUSDT** - Sui
18. **SEIUSDT** - Sei
19. **TIAUSDT** - Celestia
20. **PENDLEUSDT** - Pendle

## Usage

### Run All 20 Coins in Parallel

```bash
python historical_runner.py \
  --symbols BTCUSDT ETHUSDT BNBUSDT SOLUSDT ADAUSDT AVAXUSDT MATICUSDT DOTUSDT LINKUSDT ATOMUSDT NEARUSDT APTUSDT ARBUSDT OPUSDT RUNEUSDT INJUSDT SUIUSDT SEIUSDT TIAUSDT PENDLEUSDT \
  --start-date 2024-01-01 \
  --end-date 2024-01-07 \
  --max-workers 10
```

### Run by Tier

**Tier 1 only (safer, higher liquidity):**
```bash
python historical_runner.py \
  --symbols BTCUSDT ETHUSDT BNBUSDT SOLUSDT ADAUSDT \
  --start-date 2024-01-01 \
  --end-date 2024-01-07
```

**Tier 2-3 (mid + high vol):**
```bash
python historical_runner.py \
  --symbols AVAXUSDT MATICUSDT DOTUSDT LINKUSDT ATOMUSDT NEARUSDT APTUSDT ARBUSDT OPUSDT RUNEUSDT \
  --start-date 2024-01-01 \
  --end-date 2024-01-07 \
  --max-workers 10
```

## Notes

- All pairs have high liquidity on Binance
- USDT pairs for consistent base currency
- Avoid low liquidity pairs that may have data gaps
- Adjust `--max-workers` based on your CPU (4-10 recommended)
