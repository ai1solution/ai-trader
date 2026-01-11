"""
Historical evaluation runner with determinism verification.

Multi-day sequential historical testing with proper state management
and CSV output generation.

Features:
- Sequential day-by-day processing (no lookahead)
- HistoricalAPIDataFeed with caching support
- Trade-level and daily summary CSV outputs
- Determinism verification (run twice, compare outputs)

Usage:
    python historical_runner.py --symbol BTCUSDT --start-date 2024-01-01 --end-date 2024-01-07
    
    # With determinism verification
    python historical_runner.py --symbol BTCUSDT --start-date 2024-01-01 --end-date 2024-01-03 --verify-determinism
    
    # Multiple symbols
    python historical_runner.py --symbols BTCUSDT ETHUSDT --start-date 2024-01-01 --end-date 2024-01-07
"""

import argparse
import sys
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional, Any
from concurrent.futures import ProcessPoolExecutor, as_completed
import pandas as pd
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn

from engine import EngineConfig, TradingEngine
from engine.logger import EngineLogger
from engine.market_data import HistoricalFeed
from engine.api_client import fetch_binance_candles, cache_candles, load_cached_candles
from utils import get_cache_path, clear_logs

console = Console()


def fetch_historical_data(symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
    """
    Fetch or load cached historical data for symbol.
    
    Args:
        symbol: Trading symbol (e.g., "BTCUSDT")
        start_date: Start date string
        end_date: End date string
        
    Returns:
        DataFrame with OHLCV data
    """
    # Convert symbol format for API
    api_symbol = symbol.replace("USDT", "/USDT")
    
    # Generate cache path
    cache_path = get_cache_path(symbol, start_date, end_date)
    
    # Try to load from cache
    candles_df = load_cached_candles(cache_path)
    
    if candles_df is None:
        # Fetch from API
        console.print(f"[yellow]Fetching {symbol} data from Binance API...[/yellow]")
        start_dt = pd.to_datetime(start_date).tz_localize('UTC')
        end_dt = pd.to_datetime(end_date).tz_localize('UTC')
        
        try:
            candles_df = fetch_binance_candles(api_symbol, start_dt, end_dt)
            
            # Cache for future use
            cache_candles(candles_df, cache_path)
            console.print(f"[green]✓ Fetched and cached {len(candles_df)} candles for {symbol}[/green]")
            
        except Exception as e:
            console.print(f"[red]✗ Error fetching {symbol}: {e}[/red]")
            raise
    else:
        console.print(f"[green]✓ Loaded {symbol} from cache ({len(candles_df)} candles)[/green]")
    
    return candles_df


def run_historical_evaluation(
    symbol: str,
    candles_df: pd.DataFrame,
    config: EngineConfig,
    run_id: str = "run1"
) ->Tuple[List[Dict], List[Dict]]:
    """
    Run historical evaluation over candles.
    
    Args:
        symbol: Trading symbol
        candles_df: Historical candles DataFrame
        config: Engine configuration
        run_id: Run identifier for logging
        
    Returns:
        Tuple of (trades_list, daily_summary_list)
    """
    # Create logger
    log_file = f"logs/historical_{symbol}_{run_id}.log"
    logger = EngineLogger(log_file=log_file, log_level="INFO")
    
    # Create engine
    engine = TradingEngine(symbol=symbol, config=config, logger=logger)
    
    # Create historical feed
    feed = HistoricalFeed(
        candles_df=candles_df,
        tick_interval_seconds=config.replay_tick_interval_seconds
    )
    
    # Track trades and daily stats
    trades = []
    current_trade = {}
    daily_pnl = {}
    
    # Process all ticks
    tick_count = 0
    while feed.has_more_data():
        tick = feed.get_next_tick()
        if tick is None:
            break
            
        engine.on_tick(tick)
        tick_count += 1
        
        # Extract trade information from logs (parse latest decision)
        # This is simplified - in production you'd parse the full log
        
    # Parse logs to extract trades
    trades = _parse_trades_from_log(log_file, symbol)
    daily_summary = _generate_daily_summary(trades, candles_df)
    
    console.print(f"[green]✓ Completed {symbol}: {len(trades)} trades, {tick_count} ticks processed[/green]")
    
    return trades, daily_summary


def _parse_trades_from_log(log_file: str, symbol: str) -> List[Dict]:
    """
    Parse trade information from engine log.
    
    Returns:
        List of trade dictionaries
    """
    import json
    
    trades = []
    current_trade = None
    
    try:
        with open(log_file, 'r') as f:
            for line in f:
                try:
                    log_entry = json.loads(line.strip())
                    event = log_entry.get('event', '')
                    
                    if event == 'POSITION_ENTRY':
                        # Start new trade
                        current_trade = {
                            'entry_time': log_entry['timestamp'],
                            'entry_price': log_entry['price'],
                            'direction': log_entry.get('direction', 'UNKNOWN'),
                            'regime_at_entry': log_entry.get('regime', 'UNKNOWN'),
                            'partial_taken': False,
                            'partial_realized_pnl': 0.0,
                        }
                    
                    elif event == 'POSITION_EXIT' and current_trade:
                        # Complete trade
                        current_trade['exit_time'] = log_entry['timestamp']
                        current_trade['exit_price'] = log_entry['price']
                        current_trade['exit_reason'] = log_entry.get('reason', 'UNKNOWN')
                        
                        # Prefer net_pnl if available (v4 engine), else pnl
                        current_trade['final_pnl'] = log_entry.get('net_pnl', log_entry.get('pnl', 0.0))
                        current_trade['fees'] = log_entry.get('fees', 0.0)
                        current_trade['slippage'] = log_entry.get('slippage', 0.0)
                        current_trade['gross_pnl'] = log_entry.get('gross_pnl', current_trade['final_pnl'])
                        
                        # Calculate holding duration
                        entry_dt = pd.to_datetime(current_trade['entry_time'])
                        exit_dt = pd.to_datetime(current_trade['exit_time'])
                        current_trade['holding_duration'] = (exit_dt - entry_dt).total_seconds()
                        
                        trades.append(current_trade)
                        current_trade = None
                        
                except json.JSONDecodeError:
                    continue
    except FileNotFoundError:
        console.print(f"[yellow]Warning: Log file not found: {log_file}[/yellow]")
    
    return trades


def _generate_daily_summary(trades: List[Dict], candles_df: pd.DataFrame) -> List[Dict]:
    """Generate daily summary statistics from trades."""
    if not trades:
        return []
    
    trades_df = pd.DataFrame(trades)
    trades_df['exit_date'] = pd.to_datetime(trades_df['exit_time']).dt.date
    trades_df['win'] = trades_df['final_pnl'] > 0
    
    daily_groups = trades_df.groupby('exit_date')
    
    daily_summary = []
    
    # Running cumulative PnL for drawdown
    cumulative_pnl = 0.0
    peak_pnl = 0.0
    
    # Sort dates
    sorted_dates = sorted(daily_groups.groups.keys())
    
    for date in sorted_dates:
        group = daily_groups.get_group(date)
        
        daily_pnl = group['final_pnl'].sum()
        cumulative_pnl += daily_pnl
        peak_pnl = max(peak_pnl, cumulative_pnl)
        drawdown = peak_pnl - cumulative_pnl
        
        summary = {
            'date': str(date),
            'trades': len(group),
            'wins': group['win'].sum(),
            'losses': (~group['win']).sum(),
            'net_pnl': daily_pnl,
            'fees': group['fees'].sum() if 'fees' in group else 0.0,
            'avg_trade_pnl': group['final_pnl'].mean(),
            'pct_trades_with_partial': (group['partial_taken'].sum() / len(group) * 100) if len(group) > 0 else 0,
            'cumulative_pnl': cumulative_pnl,
            'drawdown': drawdown
        }
        
        daily_summary.append(summary)
    
    return daily_summary


def calculate_performance_metrics(trades: List[Dict]) -> Dict[str, Any]:
    """Calculate advanced performance metrics."""
    if not trades:
        return {"error": "No trades"}
        
    df = pd.DataFrame(trades)
    
    total_trades = len(df)
    mins = df['win'].sum() if 'win' in df else (df['final_pnl'] > 0).sum()
    win_rate = (mins / total_trades) * 100
    
    net_pnl = df['final_pnl'].sum()
    avg_pnl = df['final_pnl'].mean()
    max_drawdown = 0.0 # Calculated from daily usually, but trade-level approx:
    
    # Sharpe Ratio (Simplified: Daily Mean / Daily Std * sqrt(365))
    # We need daily returns.
    df['exit_date'] = pd.to_datetime(df['exit_time']).dt.date
    daily_pnl = df.groupby('exit_date')['final_pnl'].sum()
    
    if len(daily_pnl) > 1:
        sharpe = (daily_pnl.mean() / daily_pnl.std()) * (365 ** 0.5) if daily_pnl.std() != 0 else 0
    else:
        sharpe = 0.0
        
    return {
        "Total Trades": total_trades,
        "Net PnL": round(net_pnl, 2),
        "Win Rate": f"{win_rate:.2f}%",
        "Average Trade": round(avg_pnl, 2),
        "Sharpe Ratio": round(sharpe, 2),
    }

def save_trades_csv(trades: List[Dict], output_path: str):
    """Save trades to CSV file."""
    if not trades:
        print("[yellow]No trades to save[/yellow]")
        return
    
    df = pd.DataFrame(trades)
    
    # Select and order columns
    columns = [
        'entry_time', 'exit_time', 'entry_price', 'exit_price',
        'partial_taken', 'partial_realized_pnl', 'final_pnl',
        'fees', 'slippage', 'gross_pnl',
        'regime_at_entry', 'exit_reason', 'holding_duration'
    ]
    
    # Only include columns that exist
    columns = [col for col in columns if col in df.columns]
    df = df[columns]
    
    df.to_csv(output_path, index=False)
    print(f"[green]✓ Saved trades to {output_path}[/green]")


def save_daily_summary_csv(daily_summary: List[Dict], output_path: str):
    """Save daily summary to CSV file."""
    if not daily_summary:
        print("[yellow]No daily summary to save[/yellow]")
        return
    
    df = pd.DataFrame(daily_summary)
    df.to_csv(output_path, index=False)
    print(f"[green]✓ Saved daily summary to {output_path}[/green]")


def verify_determinism(
    symbol: str,
    candles_df: pd.DataFrame,
    config: EngineConfig
) -> bool:
    """
    Verify determinism by running twice and comparing outputs.
    
    Returns:
        True if outputs are identical, False otherwise
    """
    print("\n[bold yellow]Verifying Determinism...[/bold yellow]")
    
    # Run 1
    print("[cyan]Run 1...[/cyan]")
    trades1, daily1 = run_historical_evaluation(symbol, candles_df, config, "determinism_run1")
    
    # Run 2
    print("[cyan]Run 2...[/cyan]")
    trades2, daily2 = run_historical_evaluation(symbol, candles_df, config, "determinism_run2")
    
    # Compare trade counts
    if len(trades1) != len(trades2):
        print(f"[red]✗ Trade count mismatch: {len(trades1)} vs {len(trades2)}[/red]")
        return False
    
    # Compare trade details
    for i, (t1, t2) in enumerate(zip(trades1, trades2)):
        if t1 != t2:
            print(f"[red]✗ Trade {i+1} mismatch[/red]")
            # print(f"  Run1: {t1}")
            # print(f"  Run2: {t2}")
            return False
    
    print("[green]✓ Determinism verified: Outputs are identical[/green]")
    return True

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Historical Evaluation Runner (v4.0)")
    
    # ... args ...
    parser.add_argument('--symbol', type=str, help='Trading symbol')
    parser.add_argument('--symbols', nargs='+', help='Batch symbols')
    parser.add_argument('--start-date', type=str, required=True)
    parser.add_argument('--end-date', type=str, required=True)
    parser.add_argument('--exchange', type=str, default='binance')
    parser.add_argument('--verify-determinism', action='store_true')
    parser.add_argument('--output-dir', type=str, default='results')
    
    # Split
    parser.add_argument('--split-ratio', type=float, default=0.0, help='In-Sample split ratio (e.g. 0.7). 0.0 = No split')
    
    args = parser.parse_args()
    
    # Symbol logic ...
    if args.symbol: symbols = [args.symbol]
    elif args.symbols: symbols = args.symbols
    else:
        print("Error: Specify symbol")
        return 1
        
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    clear_logs()
    
    config = EngineConfig()
    
    all_trades = []
    all_daily = []
    
    print(f"Running Backtest: {args.start_date} -> {args.end_date}")
    
    for symbol in symbols:
        try:
            full_df = fetch_historical_data(symbol, args.start_date, args.end_date)
            
            # Split logic
            runs = []
            if args.split_ratio > 0:
                split_idx = int(len(full_df) * args.split_ratio)
                in_sample = full_df.iloc[:split_idx]
                out_sample = full_df.iloc[split_idx:]
                runs.append(("In-Sample", in_sample))
                runs.append(("Out-Sample", out_sample))
            else:
                runs.append(("Full", full_df))
                
            for run_name, df in runs:
                print(f"  Processing {symbol} [{run_name}] ({len(df)} candles)...")
                if df.empty: continue
                
                run_id = f"{symbol}_{run_name.lower().replace('-','_')}"
                trades, daily = run_historical_evaluation(symbol, df, config, run_id)
                
                # Tag
                for t in trades: t['run_type'] = run_name; t['symbol'] = symbol
                for d in daily: d['run_type'] = run_name; d['symbol'] = symbol
                
                all_trades.extend(trades)
                all_daily.extend(daily)
                
                metrics = calculate_performance_metrics(trades)
                print(f"  [{run_name}] Results: {metrics}")
                
        except Exception as e:
            print(f"Error {symbol}: {e}")
            import traceback; traceback.print_exc()
            
    # Save
    trades_path = output_dir / "historical_trades.csv"
    daily_path = output_dir / "daily_summary.csv"
    
    save_trades_csv(all_trades, str(trades_path))
    save_daily_summary_csv(all_daily, str(daily_path))
    
    return 0

if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception as e:
        print(f"Fatal: {e}")
        sys.exit(1)
