"""
Historical backtest CLI command with multi-symbol parallel execution.

Features:
- Auto-fetch data from Binance API
- Smart caching per symbol
- Parallel execution across symbols using ProcessPoolExecutor
- Comprehensive per-symbol and aggregated results
- Clean logs before run

Usage:
    # Single symbol
    python backtest.py --symbols BTCUSDT --start 2024-01-01 --end 2024-01-02
    
    # Multiple symbols (parallel)
    python backtest.py --symbols BTCUSDT ETHUSDT BNBUSDT --start 2024-01-01 --end 2024-01-02
    
    # With config overrides
    python backtest.py --symbols BTCUSDT --start 2024-01-01 --end 2024-01-02 --arm-velocity 0.01
"""

import argparse
import sys
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime
import pandas as pd

from engine import EngineConfig
from engine.api_client import fetch_binance_candles, cache_candles, load_cached_candles
from utils import (
    clear_logs, get_cache_path, format_summary, format_aggregated_summary,
    aggregate_results, run_backtest_single_symbol
)
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn

console = Console()


def fetch_data_for_symbol(symbol: str, start_date: str, end_date: str) -> Path:
    """
    Fetch or load cached data for a single symbol.
    
    Args:
        symbol: Trading symbol (e.g., "BTCUSDT")
        start_date: Start date string
        end_date: End date string
        
    Returns:
        Path to data file
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
    
    return cache_path


def main():
    """Main entry point for backtest command."""
    parser = argparse.ArgumentParser(
        description="Historical Backtest - Multi-Symbol Parallel Execution",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Single symbol backtest
  python backtest.py --symbols BTCUSDT --start 2024-01-01 --end 2024-01-02
  
  # Multi-symbol parallel backtest
  python backtest.py --symbols BTCUSDT ETHUSDT BNBUSDT --start 2024-01-01 --end 2024-01-02
  
  # With config overrides
  python backtest.py --symbols BTCUSDT --start 2024-01-01 --end 2024-01-02 --arm-velocity 0.01 --atr-stop 3.0
        """
    )
    
    # Required arguments
    parser.add_argument(
        '--symbols',
        nargs='+',
        required=True,
        help='One or more trading symbols (e.g., BTCUSDT ETHUSDT)'
    )
    
    parser.add_argument(
        '--start',
        type=str,
        required=True,
        help='Start date (YYYY-MM-DD or YYYY-MM-DD HH:MM:SS)'
    )
    
    parser.add_argument(
        '--end',
        type=str,
        required=True,
        help='End date (YYYY-MM-DD or YYYY-MM-DD HH:MM:SS)'
    )
    
    # Config overrides
    parser.add_argument('--arm-velocity', type=float, help='ARM velocity threshold (default: 0.005)')
    parser.add_argument('--arm-persistence', type=int, help='ARM persistence ticks (default: 5)')
    parser.add_argument('--atr-stop', type=float, help='ATR stop multiplier (default: 2.0)')
    parser.add_argument('--trailing-stop', type=float, help='Trailing stop %% (default: 0.02)')
    parser.add_argument('--log-level', type=str, choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], default='INFO')
    
    # Execution options
    parser.add_argument('--max-workers', type=int, default=4, help='Max parallel workers (default: 4)')
    parser.add_argument('--no-clear-logs', action='store_true', help='Do not clear logs before run')
    
    args = parser.parse_args()
    
    # Print header
    console.print("\n" + "="*80, style="bold blue")
    console.print("CRYPTO TRADING ENGINE - HISTORICAL BACKTEST", style="bold blue", justify="center")
    console.print("="*80, style="bold blue")
    console.print()
    
    console.print(f"[cyan]Symbols:[/cyan] {', '.join(args.symbols)}")
    console.print(f"[cyan]Date Range:[/cyan] {args.start} → {args.end}")
    console.print(f"[cyan]Workers:[/cyan] {args.max_workers}")
    console.print()
    
    # Clear logs
    if not args.no_clear_logs:
        clear_logs()
    
    # Create config
    config = EngineConfig(
        arm_velocity_threshold=args.arm_velocity or 0.005,
        arm_persistence_ticks=args.arm_persistence or 5,
        atr_stop_multiplier=args.atr_stop or 2.0,
        trailing_stop_pct=args.trailing_stop or 0.02,
        log_level=args.log_level,
    )
    
    console.print("[cyan]Configuration:[/cyan]")
    console.print(f"  ARM Velocity: {config.arm_velocity_threshold}")
    console.print(f"  ARM Persistence: {config.arm_persistence_ticks} ticks")
    console.print(f"  ATR Stop: {config.atr_stop_multiplier}x")
    console.print(f"  Trailing Stop: {config.trailing_stop_pct*100}%%")
    console.print()
    
    # Step 1: Fetch/load data for all symbols
    console.print("="*80, style="bold")
    console.print("[bold]Step 1: Fetching Data[/bold]")
    console.print("="*80, style="bold")
    
    try:
        for symbol in args.symbols:
            fetch_data_for_symbol(symbol, args.start, args.end)
        console.print()
    except Exception as e:
        console.print(f"[red]✗ Data fetch failed: {e}[/red]")
        return 1
    
    # Step 2: Run backtests in parallel
    console.print("="*80, style="bold")
    console.print("[bold]Step 2: Running Backtests[/bold]")
    console.print("="*80, style="bold")
    console.print()
    
    # Prepare arguments for parallel execution
    config_dict = {
        'arm_velocity_threshold': config.arm_velocity_threshold,
        'arm_persistence_ticks': config.arm_persistence_ticks,
        'atr_stop_multiplier': config.atr_stop_multiplier,
        'trailing_stop_pct': config.trailing_stop_pct,
        'log_level': config.log_level,
    }
    
    backtest_args = [
        (symbol, args.start, args.end, config_dict)
        for symbol in args.symbols
    ]
    
    results = []
    
    if len(args.symbols) == 1:
        # Single symbol - run directly (no multiprocessing overhead)
        console.print(f"[yellow]Running backtest for {args.symbols[0]}...[/yellow]")
        result = run_backtest_single_symbol(backtest_args[0])
        results.append(result)
        console.print()
    else:
        # Multiple symbols - parallel execution
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=console
        ) as progress:
            
            task = progress.add_task(
                f"[cyan]Running {len(args.symbols)} backtests in parallel...",
                total=len(args.symbols)
            )
            
            with ProcessPoolExecutor(max_workers=args.max_workers) as executor:
                futures = {
                    executor.submit(run_backtest_single_symbol, arg): arg[0]
                    for arg in backtest_args
                }
                
                for future in as_completed(futures):
                    symbol = futures[future]
                    try:
                        result = future.result()
                        results.append(result)
                        progress.update(task, advance=1)
                        console.print(f"[green]✓ Completed: {symbol}[/green]")
                    except Exception as e:
                        console.print(f"[red]✗ Failed: {symbol} - {e}[/red]")
                        results.append((symbol, None))
                        progress.update(task, advance=1)
        
        console.print()
    
    # Step 3: Display results
    console.print("="*80, style="bold")
    console.print("[bold]Step 3: Results[/bold]")
    console.print("="*80, style="bold")
    console.print()
    
    # Aggregate results
    aggregated = aggregate_results(results)
    
    if not aggregated:
        console.print("[red]No successful backtests![/red]")
        return 1
    
    # Display per-symbol summaries
    if len(args.symbols) == 1:
        # Single symbol - simple format
        symbol, stats = results[0]
        if stats:
            print(format_summary(symbol, stats, stats.get('duration_seconds', 0)))
        else:
            console.print(f"[red]Backtest failed for {symbol}[/red]")
    else:
        # Multiple symbols - aggregated format
        format_aggregated_summary(aggregated)
    
    console.print("[green]✓ Backtest complete![/green]")
    console.print(f"[cyan]Logs saved to: logs/[/cyan]")
    console.print()
    
    return 0


if __name__ == '__main__':
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        console.print("\n[yellow]Backtest cancelled by user[/yellow]")
        sys.exit(130)
    except Exception as e:
        console.print(f"\n[red]Fatal error: {e}[/red]")
        import traceback
        traceback.print_exc()
        sys.exit(1)
