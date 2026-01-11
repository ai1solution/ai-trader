# Commands to Run New AI & Meme Coins

Here are the commands to execute the trading engines with the newly added 16 coins (AI/Data + Meme).

## 1. Run v4 Engine (Paper Trading)
Configuration is already updated in `v4/config.yaml`.
```powershell
python v4/main.py --no-ui
```

## 2. Run v3 Engine (Live Mock Dashboard)
You need to pass the symbols explicitly to the live runner.
```powershell
python v3/live_mock.py --symbols FETUSDT RNDRUSDT WLDUSDT GRTUSDT TAOUSDT ARKMUSDT AIUSDT NFPUSDT PHBUSDT NEARUSDT PEPEUSDT BONKUSDT WIFUSDT FLOKIUSDT MEMEUSDT BOMEUSDT
```

### Tips
- Run these in **separate terminals**.
- To stop, press `Ctrl+C`.
- Logs are saved to `logs/`.
