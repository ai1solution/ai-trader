"""
Utility functions for trading engine CLI commands.

Includes:
- Log and cache management
- Result formatting and aggregation
- Worker functions for parallel execution
"""

import shutil
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()

def round_price(price: float) -> float:
    """Round price to 8 decimal places."""
    return round(price, 8)

def round_qty(qty: float) -> float:
    """Round quantity down to 8 decimal places."""
    import math
    factor = 10**8
    return math.floor(qty * factor) / factor



def clear_logs(logs_dir: Path = Path("logs")) -> None:
    """
    Clear all log files from logs directory.
    
    Args:
        logs_dir: Path to logs directory (default: ./logs)
    """
    if logs_dir.exists():
        for file in logs_dir.glob("*"):
            if file.is_file():
                try:
                    file.unlink()
                except OSError as e:
                    console.print(f"[yellow]⚠ Could not delete {file.name}: {e}[/yellow]")
        console.print(f"✓ Cleared logs directory: {logs_dir}", style="green")
    else:
        logs_dir.mkdir(parents=True, exist_ok=True)
        console.print(f"✓ Created logs directory: {logs_dir}", style="green")


def clear_data_cache(data_dir: Path = Path("data"), confirm: bool = True) -> None:
    """
    Clear cached data files.
    
    Args:
        data_dir: Path to data directory (default: ./data)
        confirm: Ask for confirmation before deleting (default: True)
    """
    if not data_dir.exists():
        return
    
    cache_files = list(data_dir.glob("*.parquet")) + list(data_dir.glob("*.csv"))
    
    if not cache_files:
        console.print("No cache files found.", style="yellow")
        return
    
    if confirm:
        console.print(f"Found {len(cache_files)} cache files in {data_dir}")
        response = input("Delete all cache files? (y/N): ")
        if response.lower() != 'y':
            console.print("Cache deletion cancelled.", style="yellow")
            return
    
    for file in cache_files:
        file.unlink()
    
    console.print(f"✓ Cleared {len(cache_files)} cache files", style="green")


def get_cache_path(symbol: str, start_date: str, end_date: str, data_dir: Path = Path("data")) -> Path:
    """
    Generate standardized cache file path for a symbol/date range.
    
    Args:
        symbol: Trading symbol (e.g., "BTCUSDT")
        start_date: Start date string
        end_date: End date string
        data_dir: Data directory path
        
    Returns:
        Path object for cache file
    """
    # Sanitize dates for filename
    start_clean = start_date.replace("-", "").replace(":", "").replace(" ", "_")[:8]
    end_clean = end_date.replace("-", "").replace(":", "").replace(" ", "_")[:8]
    
    filename = f"{symbol}_{start_clean}_{end_clean}.parquet"
    return data_dir / filename


def format_summary(symbol: str, stats: Dict[str, Any], duration: float) -> str:
    """
    Format engine statistics into readable summary.
    
    Args:
        symbol: Trading symbol
        stats: Engine statistics dictionary
        duration: Replay duration in seconds
        
    Returns:
        Formatted summary string
    """
    lines = []
    lines.append(f"\n{'='*60}")
    lines.append(f"SUMMARY: {symbol}")
    lines.append(f"{'='*60}")
    
    lines.append(f"\nExecution Time: {duration:.2f}s")
    lines.append(f"Total Ticks: {stats.get('total_ticks', 0):,}")
    
    lines.append(f"\nTrades:")
    lines.append(f"  Total: {stats.get('total_trades', 0)}")
    lines.append(f"  Wins: {stats.get('winning_trades', 0)}")
    lines.append(f"  Losses: {stats.get('losing_trades', 0)}")
    
    win_rate = stats.get('win_rate', 0.0)
    lines.append(f"  Win Rate: {win_rate:.1f}%")
    
    lines.append(f"\nP&L:")
    total_pnl = stats.get('total_pnl', 0.0)
    pnl_style = "green" if total_pnl >= 0 else "red"
    lines.append(f"  Total: ${total_pnl:,.2f}")
    lines.append(f"  Average per Trade: ${stats.get('avg_pnl_per_trade', 0.0):,.2f}")
    
    if stats.get('best_trade'):
        lines.append(f"  Best Trade: ${stats.get('best_trade', 0.0):,.2f}")
    if stats.get('worst_trade'):
        lines.append(f"  Worst Trade: ${stats.get('worst_trade', 0.0):,.2f}")
    
    lines.append(f"\n{'='*60}\n")
    
    return "\n".join(lines)


def format_aggregated_summary(results: Dict[str, Dict[str, Any]]) -> None:
    """
    Format multi-symbol results with comparison table using Rich.
    
    Args:
        results: Dictionary mapping symbol -> stats
    """
    console.print("\n")
    console.print("="*80, style="bold blue")
    console.print("AGGREGATED RESULTS - MULTI-SYMBOL BACKTEST", style="bold blue", justify="center")
    console.print("="*80, style="bold blue")
    
    # Create comparison table
    table = Table(title="\nPer-Symbol Performance", show_header=True, header_style="bold cyan")
    table.add_column("Symbol", style="white", width=12)
    table.add_column("Trades", justify="right", style="white")
    table.add_column("Win Rate", justify="right", style="white")
    table.add_column("Total PnL", justify="right")
    table.add_column("Avg PnL/Trade", justify="right")
    table.add_column("Best Trade", justify="right", style="green")
    table.add_column("Worst Trade", justify="right", style="red")
    
    total_trades = 0
    total_wins = 0
    total_pnl = 0.0
    
    for symbol, stats in sorted(results.items()):
        trades = stats.get('total_trades', 0)
        wins = stats.get('winning_trades', 0)
        win_rate = stats.get('win_rate', 0.0)
        pnl = stats.get('total_pnl', 0.0)
        avg_pnl = stats.get('avg_pnl_per_trade', 0.0)
        best = stats.get('best_trade', 0.0)
        worst = stats.get('worst_trade', 0.0)
        
        total_trades += trades
        total_wins += wins
        total_pnl += pnl
        
        # Color-code PnL
        pnl_style = "green" if pnl >= 0 else "red"
        avg_style = "green" if avg_pnl >= 0 else "red"
        
        table.add_row(
            symbol,
            str(trades),
            f"{win_rate:.1f}%",
            f"[{pnl_style}]${pnl:,.2f}[/{pnl_style}]",
            f"[{avg_style}]${avg_pnl:,.2f}[/{avg_style}]",
            f"${best:,.2f}",
            f"${worst:,.2f}"
        )
    
    console.print(table)
    
    # Aggregated stats
    overall_win_rate = (total_wins / total_trades * 100) if total_trades > 0 else 0.0
    avg_pnl_overall = total_pnl / total_trades if total_trades > 0 else 0.0
    
    console.print("\n")
    agg_table = Table(title="Aggregated Statistics", show_header=True, header_style="bold yellow")
    agg_table.add_column("Metric", style="white")
    agg_table.add_column("Value", justify="right", style="bold white")
    
    agg_table.add_row("Total Symbols", str(len(results)))
    agg_table.add_row("Total Trades", str(total_trades))
    agg_table.add_row("Overall Win Rate", f"{overall_win_rate:.1f}%")
    
    pnl_color = "green" if total_pnl >= 0 else "red"
    agg_table.add_row("Combined PnL", f"[{pnl_color}]${total_pnl:,.2f}[/{pnl_color}]")
    agg_table.add_row("Avg PnL/Trade", f"${avg_pnl_overall:,.2f}")
    
    console.print(agg_table)
    console.print("\n" + "="*80, style="bold blue")
    console.print()


def aggregate_results(results: List[tuple]) -> Dict[str, Dict[str, Any]]:
    """
    Combine results from multiple symbol runs.
    
    Args:
        results: List of (symbol, stats) tuples
        
    Returns:
        Dictionary mapping symbol -> stats
    """
    aggregated = {}
    
    for symbol, stats in results:
        if stats:  # Only include successful runs
            aggregated[symbol] = stats
    
    return aggregated


def run_backtest_single_symbol(args: tuple) -> tuple:
    """
    Worker function for parallel backtest execution.
    
    This function is designed to be called by ProcessPoolExecutor.
    
    Args:
        args: Tuple of (symbol, start_date, end_date, config_dict)
        
    Returns:
        Tuple of (symbol, stats_dict)
    """
    from engine import EngineConfig, run_replay_from_config
    from engine.api_client import fetch_binance_candles, cache_candles, load_cached_candles
    from datetime import datetime
    import pandas as pd
    
    symbol, start_date, end_date, config_dict = args
    
    try:
        # Convert symbol format for API (BTCUSDT -> BTC/USDT)
        api_symbol = symbol.replace("USDT", "/USDT")
        
        # Generate cache path
        cache_path = get_cache_path(symbol, start_date, end_date)
        
        # Try to load from cache
        candles_df = load_cached_candles(cache_path)
        
        if candles_df is None:
            # Fetch from API
            print(f"[{symbol}] Fetching data from Binance...")
            start_dt = pd.to_datetime(start_date).tz_localize('UTC')
            end_dt = pd.to_datetime(end_date).tz_localize('UTC')
            
            candles_df = fetch_binance_candles(api_symbol, start_dt, end_dt)
            
            # Cache for future use
            cache_candles(candles_df, cache_path)
        else:
            print(f"[{symbol}] Loaded from cache")
        
        # Save to temp CSV for replay runner
        temp_file = Path(f"data/{symbol}_temp.csv")
        candles_df.to_csv(temp_file, index=False)
        
        # Create config from dict
        config = EngineConfig(**config_dict)
        
        # Run backtest
        print(f"[{symbol}] Running backtest...")
        stats = run_replay_from_config(
            symbol=symbol,
            file_path=str(temp_file),
            start_date=start_date,
            end_date=end_date,
            config=config
        )
        
        # Clean up temp file
        temp_file.unlink()
        
        return (symbol, stats)
        
    except Exception as e:
        print(f"[{symbol}] ERROR: {e}")
        return (symbol, None)
