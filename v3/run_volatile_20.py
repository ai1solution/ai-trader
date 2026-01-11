"""
Parallel historical runner for multiple volatile cryptocurrencies.

Runs historical evaluation for 20 high-volatility coins in parallel using ProcessPoolExecutor.

Usage:
    python run_volatile_20.py --start-date 2024-01-01 --end-date 2024-01-07
    
    # Custom max workers
    python run_volatile_20.py --start-date 2024-01-01 --end-date 2024-01-07 --max-workers 10
"""

import argparse
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
import subprocess
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn

console = Console()

# Top 20 volatile crypto pairs
VOLATILE_COINS = [
    # Tier 1: Large Cap Volatile
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "ADAUSDT",
    # Tier 2: Mid Cap High Beta
    "AVAXUSDT", "MATICUSDT", "DOTUSDT", "LINKUSDT", "ATOMUSDT", 
    # Tier 3: High Volatility Alts
    "NEARUSDT", "APTUSDT", "ARBUSDT", "OPUSDT", "RUNEUSDT",
    # Tier 4: Emerging High Beta
    "INJUSDT", "SUIUSDT", "SEIUSDT", "TIAUSDT", "PENDLEUSDT",
    # AI / Data
    "FETUSDT", "RNDRUSDT", "WLDUSDT", "GRTUSDT", "TAOUSDT", "ARKMUSDT", "AIUSDT", "NFPUSDT", "PHBUSDT", "NEARUSDT",
    # Meme
    "PEPEUSDT", "BONKUSDT", "WIFUSDT", "FLOKIUSDT", "MEMEUSDT", "BOMEUSDT"
]


def run_symbol_evaluation(symbol: str, start_date: str, end_date: str, output_dir: str) -> tuple:
    """
    Run historical evaluation for a single symbol.
    
    Args:
        symbol: Trading symbol
        start_date: Start date string        end_date: End date string
        output_dir: Output directory for results
        
    Returns:
        (symbol, success, message) tuple
    """
    try:
        # Run historical_runner.py for this symbol
        cmd = [
            "python", "historical_runner.py",
            "--symbol", symbol,
            "--start-date", start_date,
            "--end-date", end_date,
            "--output-dir", f"{output_dir}/{symbol}"
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600  # 10 minute timeout per symbol
        )
        
        if result.returncode == 0:
            # Parse output to get trade count
            output = result.stdout
            trade_count = 0
            for line in output.split('\n'):
                if "trades," in line and "ticks processed" in line:
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if part == "trades," and i > 0:
                            trade_count = int(parts[i-1])
                            break
            
            return (symbol, True, f"{trade_count} trades")
        else:
            return (symbol, False, f"Error: {result.stderr[:200]}")
            
    except subprocess.TimeoutExpired:
        return (symbol, False, "Timeout (>10 min)")
    except Exception as e:
        return (symbol, False, f"Exception: {str(e)[:200]}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Parallel Historical Evaluation for 20 Volatile Coins"
    )
    
    parser.add_argument(
        '--start-date',
        type=str,
        required=True,
        help='Start date (YYYY-MM-DD)'
    )
    
    parser.add_argument(
        '--end-date',
        type=str,
        required=True,
        help='End date (YYYY-MM-DD)'
    )
    
    parser.add_argument(
        '--max-workers',
        type=int,
        default=10,
        help='Maximum parallel workers (default: 10)'
    )
    
    parser.add_argument(
        '--output-dir',
        type=str,
        default='results_volatile_20',
        help='Base output directory (default: results_volatile_20)'
    )
    
    parser.add_argument(
        '--symbols',
        nargs='+',
        default=VOLATILE_COINS,
        help='Override default coin list'
    )
    
    args = parser.parse_args()
    
    # Print header
    console.print("\n" + "="*80, style="bold blue")
    console.print("PARALLEL HISTORICAL EVALUATION - 20 VOLATILE COINS", style="bold blue", justify="center")
    console.print("="*80, style="bold blue")
    console.print()
    
    console.print(f"[cyan]Coins:[/cyan] {len(args.symbols)}")
    console.print(f"[cyan]Date Range:[/cyan] {args.start_date} → {args.end_date}")
    console.print(f"[cyan]Max Workers:[/cyan] {args.max_workers}")
    console.print(f"[cyan]Output Dir:[/cyan] {args.output_dir}")
    console.print()
    
    # Create base output directory
    Path(args.output_dir).mkdir(parents=True, exist_ok=True)
    
    # Run evaluations in parallel
    results = []
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        console=console
    ) as progress:
        
        task = progress.add_task(
            f"[cyan]Running {len(args.symbols)} coin evaluations in parallel...",
            total=len(args.symbols)
        )
        
        with ProcessPoolExecutor(max_workers=args.max_workers) as executor:
            # Submit all tasks
            futures = {
                executor.submit(
                    run_symbol_evaluation,
                    symbol,
                    args.start_date,
                    args.end_date,
                    args.output_dir
                ): symbol
                for symbol in args.symbols
            }
            
            # Collect results as they complete
            for future in as_completed(futures):
                symbol = futures[future]
                try:
                    symbol_result, success, message = future.result()
                    results.append((symbol_result, success, message))
                    
                    if success:
                        console.print(f"[green]✓ {symbol}: {message}[/green]")
                    else:
                        console.print(f"[red]✗ {symbol}: {message}[/red]")
                    
                    progress.update(task, advance=1)
                    
                except Exception as e:
                    console.print(f"[red]✗ {symbol}: Fatal error - {e}[/red]")
                    results.append((symbol, False, str(e)))
                    progress.update(task, advance=1)
    
    # Print summary
    console.print("\n" + "="*80, style="bold")
    console.print("RESULTS SUMMARY", style="bold", justify="center")
    console.print("="*80, style="bold")
    console.print()
    
    successful = [r for r in results if r[1]]
    failed = [r for r in results if not r[1]]
    
    console.print(f"[green]✓ Successful:[/green] {len(successful)}/{len(results)}")
    console.print(f"[red]✗ Failed:[/red] {len(failed)}/{len(results)}")
    console.print()
    
    if successful:
        console.print("[bold]Successful Evaluations:[/bold]")
        for symbol, _, message in successful:
            console.print(f"  [green]✓[/green] {symbol}: {message}")
        console.print()
    
    if failed:
        console.print("[bold]Failed Evaluations:[/bold]")
        for symbol, _, message in failed:
            console.print(f"  [red]✗[/red] {symbol}: {message}")
        console.print()
    
    # Aggregate results
    console.print(f"[cyan]Individual results saved to:[/cyan] {args.output_dir}/{{SYMBOL}}/")
    console.print(f"[cyan]Next step:[/cyan] Run analyze_historical.py on combined results")
    console.print()
    
    return 0 if len(failed) == 0 else 1


if __name__ == '__main__':
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        console.print("\n[yellow]Cancelled by user[/yellow]")
        sys.exit(130)
    except Exception as e:
        console.print(f"\n[red]Fatal error: {e}[/red]")
        import traceback
        traceback.print_exc()
        sys.exit(1)
