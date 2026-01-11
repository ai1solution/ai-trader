import argparse
import time
import logging
from rich.console import Console

from src.config import APP_NAME, VERSION, DEFAULT_CONFIG, TARGET_ASSETS
from src.utils import setup_logging
from src.feed import LiveFeed, HistoricalFeed, DataLoader
from src.engine import TradingEngine

console = Console()

def run_live():
    console.print(f"[bold red]Starting {APP_NAME} v{VERSION} (LIVE)[/bold red]")
    logger = setup_logging(log_file="logs/live_engine.log")
    
    console.print("[yellow]Initializing Market Feed...[/yellow]")
    feed = LiveFeed()
    console.print("[green]Market Feed Initialized.[/green]")

    console.print("[yellow]Initializing Trading Engine...[/yellow]")
    engine = TradingEngine(DEFAULT_CONFIG, feed)
    console.print("[green]Trading Engine Initialized.[/green]")
    
    try:
        while True:
            engine.tick()
            feed.sleep(DEFAULT_CONFIG["POLL_INTERVAL"])
    except KeyboardInterrupt:
        console.print("[yellow]Stopping Engine...[/yellow]")

def run_replay(file_path, speed):
    console.print(f"[bold cyan]Starting Replay Mode (File: {file_path})[/bold cyan]")
    logger = setup_logging(log_file="logs/replay_engine.log")
    
    # Load Data
    data = DataLoader.load_csv(file_path)
    if not data:
        console.print("[red]Failed to load replay data.[/red]")
        return

    # Determine Range
    all_ts = []
    for s in data: all_ts.extend(data[s].keys())
    if not all_ts:
        console.print("[red]No data found in file.[/red]")
        return

    start_ms = min(all_ts)
    end_ms = max(all_ts)

    feed = HistoricalFeed(data, start_ms, end_ms, speed=speed)
    
    # Override config for replay to avoid overwriting source
    config = DEFAULT_CONFIG.copy()
    config["TRAJECTORY_FILE"] = "replay_result.csv"
    engine = TradingEngine(config, feed)
    
    try:
        while not feed.is_finished():
            engine.tick()
            feed.sleep(1) # Simulated second
            
            # Progress Indication
            if feed.current_time_ms % 60000 == 0:
                 print(f"Time: {feed.now()}", end='\r')
                 
    except KeyboardInterrupt:
        console.print("[yellow]Replay Interrupted[/yellow]")
    
    console.print("[green]Replay Complete.[/green]")

def run_backtest(days):
    console.print(f"[bold blue]Starting Backtest (Last {days} Days)[/bold blue]")
    logger = setup_logging(log_file="logs/backtest_engine.log")
    
    end_ms = int(time.time() * 1000)
    start_ms = end_ms - (days * 24 * 3600 * 1000)
    
    data = DataLoader.fetch_historical('kraken', TARGET_ASSETS, start_ms, end_ms)
    if not data:
         console.print("[red]No data fetched.[/red]")
         return

    feed = HistoricalFeed(data, start_ms, end_ms, speed="max")
    engine = TradingEngine(DEFAULT_CONFIG, feed)
    
    count = 0
    try:
        while not feed.is_finished():
            engine.tick()
            feed.sleep(60) # Step by minute
            count += 1
            if count % 100 == 0:
                print(f"processed {count} candles...", end='\r')
    except KeyboardInterrupt:
         pass
         
    console.print("[green]Backtest Complete.[/green]")

def main():
    parser = argparse.ArgumentParser(description=f"{APP_NAME} Runner")
    subparsers = parser.add_subparsers(dest="command")
    
    # Live Command
    subparsers.add_parser("live", help="Run in Live Trading Mode")
    
    # Replay Command
    replay_parser = subparsers.add_parser("replay", help="Run in Replay Mode")
    replay_parser.add_argument("--file", required=True, help="Path to Trajectory CSV")
    replay_parser.add_argument("--speed", default="max", choices=["realtime", "10x", "max"])

    # Backtest Command
    backtest_parser = subparsers.add_parser("backtest", help="Run Historical Backtest")
    backtest_parser.add_argument("--days", type=int, default=3, help="Days of history to test")

    args = parser.parse_args()
    
    if args.command == "live":
        run_live()
    elif args.command == "replay":
        run_replay(args.file, args.speed)
    elif args.command == "backtest":
        run_backtest(args.days)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
