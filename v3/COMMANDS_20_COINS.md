# Quick Command Reference - 20 Volatile Coins

## ⚠️ Important: Stop Other Processes First

Before running historical evaluation, stop any running `live_mock.py` processes:
- Press `Ctrl+C` in the terminal running live_mock
- This prevents log file locking issues

---

## Historical Backtest Commands

### Test (5 coins, 1 day):
```bash
python historical_runner.py --symbols BTCUSDT ETHUSDT BNBUSDT SOLUSDT ADAUSDT --start-date 2024-01-01 --end-date 2024-01-02
```

### Full Run (20 coins, 1 week):
```bash
python historical_runner.py --symbols BTCUSDT ETHUSDT BNBUSDT SOLUSDT ADAUSDT AVAXUSDT MATICUSDT DOTUSDT LINKUSDT ATOMUSDT NEARUSDT APTUSDT ARBUSDT OPUSDT RUNEUSDT INJUSDT SUIUSDT SEIUSDT TIAUSDT PENDLEUSDT --start-date 2024-01-01 --end-date 2024-01-07
```

**Expected runtime:** ~10-15 minutes (sequential processing)

---

## Live Mock Trading Commands

### Test (5 coins):
```bash
python live_mock.py --symbols BTCUSDT ETHUSDT BNBUSDT SOLUSDT ADAUSDT
```

### Full Live (20 coins):
```bash
python live_mock.py --symbols BTCUSDT ETHUSDT BNBUSDT SOLUSDT ADAUSDT AVAXUSDT MATICUSDT DOTUSDT LINKUSDT ATOMUSDT NEARUSDT APTUSDT ARBUSDT OPUSDT RUNEUSDT INJUSDT SUIUSDT SEIUSDT TIAUSDT PENDLEUSDT
```

**Features:**
- Real-time multi-panel dashboard
- Live tick processing for all 20 symbols in parallel
- Press `Ctrl+C` to stop

---

## Single-Line Copy-Paste Commands

**Historical (20 coins):**
```
python historical_runner.py --symbols BTCUSDT ETHUSDT BNBUSDT SOLUSDT ADAUSDT AVAXUSDT MATICUSDT DOTUSDT LINKUSDT ATOMUSDT NEARUSDT APTUSDT ARBUSDT OPUSDT RUNEUSDT INJUSDT SUIUSDT SEIUSDT TIAUSDT PENDLEUSDT --start-date 2024-01-01 --end-date 2024-01-07
```

**Live Mock (20 coins):**
```
python live_mock.py --symbols BTCUSDT ETHUSDT BNBUSDT SOLUSDT ADAUSDT AVAXUSDT MATICUSDT DOTUSDT LINKUSDT ATOMUSDT NEARUSDT APTUSDT ARBUSDT OPUSDT RUNEUSDT INJUSDT SUIUSDT SEIUSDT TIAUSDT PENDLEUSDT
```

---

## Coin List (20 Total)

1. BTCUSDT - Bitcoin
2. ETHUSDT - Ethereum
3. BNBUSDT - Binance Coin
4. SOLUSDT - Solana
5. ADAUSDT - Cardano
6. AVAXUSDT - Avalanche
7. MATICUSDT - Polygon
8. DOTUSDT - Polkadot
9. LINKUSDT - Chainlink
10. ATOMUSDT - Cosmos
11. NEARUSDT - Near
12. APTUSDT - Aptos
13. ARBUSDT - Arbitrum
14. OPUSDT - Optimism
15. RUNEUSDT - THORChain
16. INJUSDT - Injective
17. SUIUSDT - Sui
18. SEIUSDT - Sei
19. TIAUSDT - Celestia
20. PENDLEUSDT - Pendle

---

## Troubleshooting

**"Process cannot access file":**
- Stop live_mock.py first (`Ctrl+C`)
- Wait 2 seconds for logs to close
- Run historical command again

**Too many symbols for screen:**
- Live mock dashboard auto-adjusts
- Scroll up/down to see all panels

**Want fewer coins:**
- Just remove symbols from the command
- Minimum 1 symbol required
