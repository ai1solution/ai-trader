"""
Analysis script for comparing v3.1 baseline vs v3.2 upgraded results.

Calculates key metrics and generates comparison reports.

Usage:
    python analyze_historical.py --trades results/historical_trades.csv
    
    # Compare against baseline
    python analyze_historical.py --baseline baseline/historical_trades.csv --upgraded results/historical_trades.csv
"""

import argparse
import sys
from pathlib import Path
import pandas as pd
import numpy as np
from rich.console import Console
from rich.table import Table

console = Console()


def calculate_metrics(trades_df: pd.DataFrame) -> dict:
    """
    Calculate comprehensive trading metrics from trades DataFrame.
    
    Args:
        trades_df: DataFrame with trade data
        
    Returns:
        Dictionary of calculated metrics
    """
    if len(trades_df) == 0:
        return {
            'total_trades': 0,
            'win_rate': 0.0,
            'total_pnl': 0.0,
            'avg_pnl_per_trade': 0.0,
            'best_trade': 0.0,
            'worst_trade': 0.0,
            'partial_take_pct': 0.0,
            'profit_factor': 0.0,
            'expectancy': 0.0,
            'max_drawdown': 0.0,
        }
    
    # Basic stats
    total_trades = len(trades_df)
    wins = (trades_df['final_pnl'] > 0).sum()
    losses = (trades_df['final_pnl'] <= 0).sum()
    win_rate = (wins / total_trades * 100) if total_trades > 0 else 0.0
    
    # PnL stats
    total_pnl = trades_df['final_pnl'].sum()
    avg_pnl = trades_df['final_pnl'].mean()
    best_trade = trades_df['final_pnl'].max()
    worst_trade = trades_df['final_pnl'].min()
    
    # Partial profit stats
    if 'partial_taken' in trades_df.columns:
        partial_taken_count = trades_df['partial_taken'].sum()
        partial_take_pct = (partial_taken_count / total_trades * 100) if total_trades > 0 else 0.0
    else:
        partial_take_pct = 0.0
    
    # Profit factor (gross wins / gross losses)
    gross_wins = trades_df[trades_df['final_pnl'] > 0]['final_pnl'].sum()
    gross_losses = abs(trades_df[trades_df['final_pnl'] <= 0]['final_pnl'].sum())
    profit_factor = (gross_wins / gross_losses) if gross_losses > 0 else 0.0
    
    # Expectancy (average win * win_rate - average loss * loss_rate)
    avg_win = trades_df[trades_df['final_pnl'] > 0]['final_pnl'].mean() if wins > 0 else 0.0
    avg_loss = abs(trades_df[trades_df['final_pnl'] <= 0]['final_pnl'].mean()) if losses > 0 else 0.0
    expectancy = (avg_win * (wins / total_trades)) - (avg_loss * (losses / total_trades)) if total_trades > 0 else 0.0
    
    # Max drawdown (simplified - cumulative PnL based)
    cumulative_pnl = trades_df['final_pnl'].cumsum()
    running_max = cumulative_pnl.expanding().max()
    drawdown = running_max - cumulative_pnl
    max_drawdown = drawdown.max()
    
    return {
        'total_trades': total_trades,
        'wins': wins,
        'losses': losses,
        'win_rate': win_rate,
        'total_pnl': total_pnl,
        'avg_pnl_per_trade': avg_pnl,
        'best_trade': best_trade,
        'worst_trade': worst_trade,
        'partial_take_pct': partial_take_pct,
        'gross_wins': gross_wins,
        'gross_losses': gross_losses,
        'profit_factor': profit_factor,
        'expectancy': expectancy,
        'max_drawdown': max_drawdown,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
    }


def print_metrics_table(metrics: dict, title: str = "Trading Metrics"):
    """Print metrics in a formatted table."""
    table = Table(title=title, show_header=True)
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    
    # Format values
    table.add_row("Total Trades", f"{metrics['total_trades']}")
    table.add_row("Wins / Losses", f"{metrics.get('wins', 0)} / {metrics.get('losses', 0)}")
    table.add_row("Win Rate", f"{metrics['win_rate']:.2f}%")
    table.add_row("Total PnL", f"${metrics['total_pnl']:.2f}")
    table.add_row("Avg PnL/Trade", f"${metrics['avg_pnl_per_trade']:.2f}")
    table.add_row("Best Trade", f"${metrics['best_trade']:.2f}")
    table.add_row("Worst Trade", f"${metrics['worst_trade']:.2f}")
    table.add_row("Max Drawdown", f"${metrics['max_drawdown']:.2f}")
    table.add_row("Partial Take %", f"{metrics['partial_take_pct']:.2f}%")
    table.add_row("Profit Factor", f"{metrics['profit_factor']:.2f}")
    table.add_row("Expectancy", f"${metrics['expectancy']:.2f}")
    
    console.print(table)


def print_comparison_table(baseline_metrics: dict, upgraded_metrics: dict):
    """Print comparison table between baseline and upgraded versions."""
    table = Table(title="v3.1 (Baseline) vs v3.2 (Upgraded) Comparison", show_header=True)
    table.add_column("Metric", style="cyan")
    table.add_column("v3.1 Baseline", style="yellow")
    table.add_column("v3.2 Upgraded", style="green")
    table.add_column("Change", style="magenta")
    
    def format_change(baseline_val, upgraded_val, is_percentage=False):
        """Format change with color."""
        if baseline_val == 0:
            return "N/A"
        change_pct = ((upgraded_val - baseline_val) / abs(baseline_val)) * 100
        sign = "+" if change_pct >= 0 else ""
        return f"{sign}{change_pct:.1f}%"
    
    # Total trades
    table.add_row(
        "Total Trades",
        f"{baseline_metrics['total_trades']}",
        f"{upgraded_metrics['total_trades']}",
        format_change(baseline_metrics['total_trades'], upgraded_metrics['total_trades'])
    )
    
    # Win rate
    table.add_row(
        "Win Rate",
        f"{baseline_metrics['win_rate']:.2f}%",
        f"{upgraded_metrics['win_rate']:.2f}%",
        f"{upgraded_metrics['win_rate'] - baseline_metrics['win_rate']:+.2f}pp"
    )
    
    # Total PnL (most important)
    table.add_row(
        "[bold]Total PnL[/bold]",
        f"[bold]${baseline_metrics['total_pnl']:.2f}[/bold]",
        f"[bold]${upgraded_metrics['total_pnl']:.2f}[/bold]",
        f"[bold]{format_change(baseline_metrics['total_pnl'], upgraded_metrics['total_pnl'])}[/bold]"
    )
    
    # Avg PnL per trade
    table.add_row(
        "Avg PnL/Trade",
        f"${baseline_metrics['avg_pnl_per_trade']:.2f}",
        f"${upgraded_metrics['avg_pnl_per_trade']:.2f}",
        format_change(baseline_metrics['avg_pnl_per_trade'], upgraded_metrics['avg_pnl_per_trade'])
    )
    
    # Max Drawdown
    table.add_row(
        "Max Drawdown",
        f"${baseline_metrics['max_drawdown']:.2f}",
        f"${upgraded_metrics['max_drawdown']:.2f}",
        format_change(baseline_metrics['max_drawdown'], upgraded_metrics['max_drawdown'])
    )
    
    # Partial take %
    table.add_row(
        "Partial Take %",
        f"{baseline_metrics['partial_take_pct']:.2f}%",
        f"{upgraded_metrics['partial_take_pct']:.2f}%",
        f"{upgraded_metrics['partial_take_pct'] - baseline_metrics['partial_take_pct']:+.2f}pp"
    )
    
    # Profit factor
    table.add_row(
        "Profit Factor",
        f"{baseline_metrics['profit_factor']:.2f}",
        f"{upgraded_metrics['profit_factor']:.2f}",
        format_change(baseline_metrics['profit_factor'], upgraded_metrics['profit_factor'])
    )
    
    # Expectancy
    table.add_row(
        "Expectancy",
        f"${baseline_metrics['expectancy']:.2f}",
        f"${upgraded_metrics['expectancy']:.2f}",
        format_change(baseline_metrics['expectancy'], upgraded_metrics['expectancy'])
    )
    
    console.print(table)


def generate_markdown_report(
    baseline_metrics: dict,
    upgraded_metrics: dict,
    output_path: str = "results/comparison_report.md"
):
    """Generate markdown comparison report."""
    
    pnl_improvement = ((upgraded_metrics['total_pnl'] - baseline_metrics['total_pnl']) / abs(baseline_metrics['total_pnl'])) * 100 if baseline_metrics['total_pnl'] != 0 else 0.0
    
    report = f"""# Trading Engine v3.1 → v3.2 Comparison Report

## Executive Summary

- **Net PnL Improvement**: {pnl_improvement:+.1f}%
- **Baseline (v3.1) Total PnL**: ${baseline_metrics['total_pnl']:.2f}
- **Upgraded (v3.2) Total PnL**: ${upgraded_metrics['total_pnl']:.2f}

## Key Metrics Comparison

| Metric | v3.1 Baseline | v3.2 Upgraded | Change |
|--------|---------------|---------------|--------|
| Total Trades | {baseline_metrics['total_trades']} | {upgraded_metrics['total_trades']} | {((upgraded_metrics['total_trades'] - baseline_metrics['total_trades']) / baseline_metrics['total_trades'] * 100):+.1f}% |
| Win Rate | {baseline_metrics['win_rate']:.2f}% | {upgraded_metrics['win_rate']:.2f}% | {upgraded_metrics['win_rate'] - baseline_metrics['win_rate']:+.2f}pp |
| Avg PnL/Trade | ${baseline_metrics['avg_pnl_per_trade']:.2f} | ${upgraded_metrics['avg_pnl_per_trade']:.2f} | {((upgraded_metrics['avg_pnl_per_trade'] - baseline_metrics['avg_pnl_per_trade']) / abs(baseline_metrics['avg_pnl_per_trade']) * 100):+.1f}% |
| Max Drawdown | ${baseline_metrics['max_drawdown']:.2f} | ${upgraded_metrics['max_drawdown']:.2f} | {((upgraded_metrics['max_drawdown'] - baseline_metrics['max_drawdown']) / baseline_metrics['max_drawdown'] * 100):+.1f}% |
| Partial Take % | {baseline_metrics['partial_take_pct']:.2f}% | {upgraded_metrics['partial_take_pct']:.2f}% | {upgraded_metrics['partial_take_pct'] - baseline_metrics['partial_take_pct']:+.2f}pp |
| Profit Factor | {baseline_metrics['profit_factor']:.2f} | {upgraded_metrics['profit_factor']:.2f} | {((upgraded_metrics['profit_factor'] - baseline_metrics['profit_factor']) / baseline_metrics['profit_factor'] * 100):+.1f}% |
| Expectancy | ${baseline_metrics['expectancy']:.2f} | ${upgraded_metrics['expectancy']:.2f if upgraded_metrics else 0:.2f} | {((upgraded_metrics['expectancy'] - baseline_metrics['expectancy']) / abs(baseline_metrics['expectancy']) * 100):+.1f}% |

## v3.2 Improvements

### A1: Regime-Aware Partial Thresholds
- TRENDING regime: 0.45% MFE threshold
- RANGING/VOLATILE regime: 0.75% MFE threshold
- Allows earlier monetization in trending markets

### A2: Post-Partial Trailing Tightening
- Trailing stop reduced by 60% after partial fires
- Converts chop into flat exits while preserving upside

### A3: Loser Suppression
- Extended cooldown (3×) after 3 consecutive stop-losses
- Reduces exposure to locally hostile conditions
- Improves equity curve smoothness

## Conclusion

{"✓ Target met!" if abs(pnl_improvement) >= 35 else "⚠ Further optimization recommended"} Net PnL improvement: **{pnl_improvement:+.1f}%**

Drawdown {'increased' if upgraded_metrics['max_drawdown'] > baseline_metrics['max_drawdown'] else 'decreased'} by {abs((upgraded_metrics['max_drawdown'] - baseline_metrics['max_drawdown']) / baseline_metrics['max_drawdown'] * 100):.1f}%

Trade frequency {' increased' if upgraded_metrics['total_trades'] > baseline_metrics['total_trades'] else 'decreased'} by {abs((upgraded_metrics['total_trades'] - baseline_metrics['total_trades']) / baseline_metrics['total_trades'] * 100):.1f}%
"""
    
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        f.write(report)
    
    console.print(f"[green]✓ Report saved to {output_path}[/green]")


def main():
    """Main entry point for analysis script."""
    parser = argparse.ArgumentParser(
        description="Analyze historical trading results and compare versions"
    )
    
    parser.add_argument(
        '--trades',
        type=str,
        help='Path to trades CSV file'
    )
    
    parser.add_argument(
        '--baseline',
        type=str,
        help='Path to baseline (v3.1) trades CSV'
    )
    
    parser.add_argument(
        '--upgraded',
        type=str,
        help='Path to upgraded (v3.2) trades CSV'
    )
    
    parser.add_argument(
        '--report',
        type=str,
        default='results/comparison_report.md',
        help='Output path for markdown report'
    )
    
    args = parser.parse_args()
    
    # Print header
    console.print("\n" + "="*80, style="bold blue")
    console.print("HISTORICAL RESULTS ANALYSIS", style="bold blue", justify="center")
    console.print("="*80, style="bold blue")
    console.print()
    
    # Single file analysis
    if args.trades:
        console.print(f"[cyan]Analyzing:[/cyan] {args.trades}")
        trades_df = pd.DataFrame(pd.read_csv(args.trades))
        metrics = calculate_metrics(trades_df)
        print_metrics_table(metrics)
        return 0
    
    # Comparison analysis
    if args.baseline and args.upgraded:
        console.print(f"[cyan]Baseline (v3.1):[/cyan] {args.baseline}")
        console.print(f"[cyan]Upgraded (v3.2):[/cyan] {args.upgraded}")
        console.print()
        
        baseline_df = pd.read_csv(args.baseline)
        upgraded_df = pd.read_csv(args.upgraded)
        
        baseline_metrics = calculate_metrics(baseline_df)
        upgraded_metrics = calculate_metrics(upgraded_df)
        
        # Print individual metrics
        console.print("\n[bold]v3.1 Baseline:[/bold]")
        print_metrics_table(baseline_metrics, "v3.1 Baseline Metrics")
        
        console.print("\n[bold]v3.2 Upgraded:[/bold]")
        print_metrics_table(upgraded_metrics, "v3.2 Upgraded Metrics")
        
        # Print comparison
        console.print()
        print_comparison_table(baseline_metrics, upgraded_metrics)
        
        # Generate report
        generate_markdown_report(baseline_metrics, upgraded_metrics, args.report)
        
        return 0
    
    console.print("[red]Error: Must specify either --trades or (--baseline AND --upgraded)[/red]")
    return 1


if __name__ == '__main__':
    try:
        exit_code = main()
        sys.exit(exit_code)
    except Exception as e:
        console.print(f"\n[red]Fatal error: {e}[/red]")
        import traceback
        traceback.print_exc()
        sys.exit(1)
