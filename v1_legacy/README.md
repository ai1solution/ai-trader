# AI Trader V11.0: "Action-First Command Center"

## Overview
The **Action-First Command Center** (V11.0) is a high-frequency cryptocurrency scalping engine designed for the Kraken exchange. It utilizes a sophisticated state machine architecture to manage trade lifecycles, ensuring disciplined execution and robust risk management.

## Key Features

### 1. State Machine Architecture
The engine operates on a strict state machine for every ticker:
-   **WAIT**: Scanning for opportunities.
-   **ARM**: Velocity threshold crossed; monitoring for signal persistence.
-   **ENTRY**: Signal confirmed; trade executed.
-   **HOLD**: Active trade management (Stop Loss, Ratchet, Signal Decay).
-   **EXIT**: Trade closed; logging outcome.
-   **COOLDOWN**: Forced pause after losses to prevent tilt/churn.

### 2. Market Regime Detection
Automatically detects the global market capability:
-   **TRENDING**: High velocity dispersion.
-   **CHOP**: Mixed signals (prevents entries).
-   **LOW_VOL**: Low activity.

### 3. Advanced Risk Management
-   **Dynamic ATR Stops**: 2.0x ATR for >$1.00, 3.0x ATR for <$1.00.
-   **Profit Ratchet**: Aggressively moves stops to breakeven (+0.75%) and locks profit (+3.0%).
-   **Signal Decay**: Exits trades early if momentum fades or reverses.
-   **Heat Governors**: Limits total active trades and exposure to correlated assets (Majors, Memes, Alts).

### 4. Professional UI (Rich)
-   **Battle Stations Panel**: Bold, clear instructions for the operator (BUY/SELL/SCANNING).
-   **Live Dashboard**: Real-time table showing Price, PnL, Velocity, and Advisor status for all tracked assets.
-   **Trajectory Logging**: Saves every scan cycle to `trajectory.csv` for AI analysis.

## Configuration
The system is configured via `config.json` (auto-generated on first run):
-   `BASE_LEVERAGE`: Default 10x.
-   `VELOCITY_THRESHOLD`: 0.15% (Dynamic based on heat).
-   `POLL_INTERVAL`: 2 seconds.
-   `ARM_PERSISTENCE`: 3 consecutive scans required to confirm entry.

## Requirements
-   Python 3.8+
-   `ccxt` (Kraken API)
-   `rich` (Terminal UI)

## Installation
```bash
pip install ccxt rich
```

## Usage
Run the engine:
```bash
python v1_legacy/trading_engine.py
```
*Note: Ensure you have valid Kraken API credentials if extending for live execution (currently uses public data for scanning).*

## Historical Analysis Tool
The project includes a standalone scraper for replaying historical data and generating analysis logs compatible with the trading engine logic.

### Usage
1. Open `historical_scraper.py`.
2. Configure `START_TIME_IST` and `END_TIME_IST` (Note: Ensure dates are recent/valid on Kraken).
3. Run the script:
   ```bash
   python historical_scraper.py
   ```
4. Analysis results are saved to `historical_trajectory_YYYYMMDD_HHMMSS.csv`.
