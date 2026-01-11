import logging
import time
import os
import sys
import ccxt
import pandas as pd
from datetime import datetime, timedelta, timezone
from rich.console import Console

# Import Engine & Feed
import trading_engine
from market_data_feed import HistoricalFeed

# Import Scraper Logic (for standardized fetching)
import historical_scraper

# --- Configuration ---
START_TIME_IST = "2025-12-26 08:00:00" # Known valid window
DURATION_HOURS = 120
REPLAY_SPEED = "max" # "realtime", "10x", "max"

REPLAY_LOG_FILE = "engine_replay_v3.log"
REPLAY_TRAJECTORY_FILE = "trajectory_replay_v3.csv"
REPLAY_STATE_FILE = "active_trades_replay_v3.json"

console = Console()

def setup_replay_environment():
    """Redirects engine outputs to replay files."""
    # Monkey-patch constants
    trading_engine.LOG_FILE = REPLAY_LOG_FILE
    trading_engine.TRAJECTORY_FILE = REPLAY_TRAJECTORY_FILE
    trading_engine.STATE_FILE = REPLAY_STATE_FILE
    
    # Clear previous replay files
    if os.path.exists(REPLAY_LOG_FILE): os.remove(REPLAY_LOG_FILE)
    if os.path.exists(REPLAY_TRAJECTORY_FILE): os.remove(REPLAY_TRAJECTORY_FILE)
    if os.path.exists(REPLAY_STATE_FILE): os.remove(REPLAY_STATE_FILE)
    
    # Re-init logging with new file
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
        
    logging.basicConfig(
        filename=REPLAY_LOG_FILE,
        level=logging.INFO,
        format='%(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

def load_data_from_csv(file_path):
    """Loads OHLCV data from a trajectory CSV."""
    console.print(f"[cyan]Loading data from {file_path}...[/cyan]")
    try:
        df = pd.read_csv(file_path)
        data = {} # {symbol: {ts: {o,h,l,c,v}}}
        
        count = 0
        for _, row in df.iterrows():
            symbol = row['Symbol']
            ts_str = row['Timestamp_IST']
            ts = historical_scraper.ist_to_utc_timestamp(ts_str)
            
            if symbol not in data: data[symbol] = {}
            
            data[symbol][ts] = {
                'o': float(row['Open']),
                'h': float(row['High']),
                'l': float(row['Low']),
                'c': float(row['Close']),
                'v': float(row['Volume'])
            }
            count += 1
            
        console.print(f"[green]Loaded {count} candles from CSV.[/green]")
        return data
    except Exception as e:
        console.print(f"[red]Failed to load CSV: {e}[/red]")
        return None

def find_latest_trajectory_csv():
    files = [f for f in os.listdir('.') if f.startswith('historical_trajectory_') and f.endswith('.csv')]
    if not files: return None
    files.sort(reverse=True) # Newest first
    return files[0]

def run_replay():
    console.print("[bold cyan]Initializing Engine Replay Runner...[/bold cyan]")
    
    # 1. Setup Environment
    setup_replay_environment()
    
    csv_file = find_latest_trajectory_csv()
    historical_data = None
    
    if csv_file:
        console.print(f"[yellow]Found local data: {csv_file}. Using it to avoid network issues.[/yellow]")
        historical_data = load_data_from_csv(csv_file)
        
        # Infer times from data if loaded
        if historical_data:
            all_ts = []
            for sym in historical_data:
                all_ts.extend(historical_data[sym].keys())
            if all_ts:
                start_ts_ms = min(all_ts)
                end_ts_ms = max(all_ts)
                console.print(f"Data Timerange: {start_ts_ms} -> {end_ts_ms}")
                console.print(f"Speed: {REPLAY_SPEED}")
    
    # 3. Fallback to Network if no data
    if not historical_data:
        start_ts_ms = historical_scraper.ist_to_utc_timestamp(START_TIME_IST)
        end_ts_ms = start_ts_ms + (DURATION_HOURS * 3600 * 1000)
        
        console.print(f"Replay Window (IST): {START_TIME_IST} -> +{DURATION_HOURS}h")
        console.print(f"Speed: {REPLAY_SPEED}")
        console.print(f"Start TS (ms): {start_ts_ms}")
        
        console.print("[yellow]Fetching Historical Data (1m OHLCV) from Network...[/yellow]")
        exchange = ccxt.kraken()
        historical_data = historical_scraper.fetch_historical_data(
            exchange, 
            trading_engine.TARGET_ASSETS, 
            start_ts_ms - (30 * 60 * 1000), 
            end_ts_ms
        )
    
    if not historical_data:
        console.print("[red]Failed to fetch data or empty result![/red]")
        return
        
    # Debug Data Stats
    total_candles = sum(len(v) for v in historical_data.values())
    console.print(f"[green]fetched {total_candles} candles total.[/green]")
    if total_candles == 0:
        console.print("[red]No candles fetched! Check network or date range.[/red]")
        return

    # 4. Initialize Feed
    # Ensure start_ts_ms is defined if we loaded from CSV
    if 'start_ts_ms' not in locals():
        all_ts = []
        for sym in historical_data:
            all_ts.extend(historical_data[sym].keys())
        start_ts_ms = min(all_ts)
        end_ts_ms = max(all_ts)

    feed = HistoricalFeed(historical_data, start_ts_ms, end_ts_ms, speed=REPLAY_SPEED)
    
    # 5. Run Engine
    console.print(f"[green]Data Loaded. Starting Engine...[/green]")
    try:
        trading_engine.run_command_center(market_feed=feed)
    except KeyboardInterrupt:
        console.print("[red]Replay Interrupted by User[/red]")
    except Exception as e:
        console.print(f"[red]Replay Error: {e}[/red]")
        logging.exception("Replay Crashed")

    console.print(f"[bold green]Replay Complete![/bold green]")
    console.print(f"Check outputs: {REPLAY_LOG_FILE}, {REPLAY_TRAJECTORY_FILE}")

if __name__ == "__main__":
    run_replay()
