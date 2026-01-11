import json
import argparse
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

def analyze_session(report_path):
    console = Console()
    
    try:
        with open(report_path, 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        console.print(f"[red]Error: File {report_path} not found.[/red]")
        return

    # Header Stats
    duration_mins = data.get('duration', 0) / 60
    initial_bal = data.get('initial_balance', 0)
    final_bal = data.get('final_balance', 0)
    pnl_pct = data.get('total_pnl_pct', 0)
    
    color = "green" if pnl_pct >= 0 else "red"
    
    console.print(Panel(
        f"Duration: {duration_mins:.1f} mins\n"
        f"Initial Balance: ${initial_bal:.2f}\n"
        f"Final Balance:   ${final_bal:.2f}\n"
        f"Total PnL:       [{color}]{pnl_pct:+.2f}%[/{color}] (${final_bal - initial_bal:+.2f})",
        title="Live Session Analysis",
        subtitle=data.get('timestamp')
    ))

    # Strategy Breakdown
    table = Table(title="Strategy Performance", show_lines=True)
    table.add_column("Strategy", style="cyan")
    table.add_column("Trades", justify="right")
    table.add_column("Wins", justify="right", style="green")
    table.add_column("Losses", justify="right", style="red")
    table.add_column("PnL ($)", justify="right")
    
    strategies = data.get('strategies', {})
    
    # Aggregated stats for coins
    coin_stats = {}
    
    for name, strategy in strategies.items():
        stats = strategy.get('stats', {})
        total_trades = sum(d['trades'] for d in stats.values())
        total_wins = sum(d['wins'] for d in stats.values())
        total_losses = sum(d['losses'] for d in stats.values())
        total_pnl = sum(d['total_pnl'] for d in stats.values())
        
        pnl_color = "green" if total_pnl > 0 else "red" if total_pnl < 0 else "white"
        
        table.add_row(
            name,
            str(total_trades),
            str(total_wins),
            str(total_losses),
            f"[{pnl_color}]{total_pnl:+.4f}[/{pnl_color}]"
        )
        
        # Aggregate coin stats
        for symbol, s in stats.items():
            if symbol not in coin_stats:
                coin_stats[symbol] = {'trades': 0, 'pnl': 0.0}
            coin_stats[symbol]['trades'] += s['trades']
            coin_stats[symbol]['pnl'] += s['total_pnl']

    console.print(table)
    
    # Best/Worst Coins
    console.print("\n[bold]Coin Performance Summary:[/bold]")
    sorted_coins = sorted(coin_stats.items(), key=lambda x: x[1]['pnl'], reverse=True)
    
    coin_table = Table(show_header=True)
    coin_table.add_column("Symbol")
    coin_table.add_column("Trades")
    coin_table.add_column("PnL")
    
    # Top 3
    for symbol, s in sorted_coins[:3]:
        if s['trades'] > 0:
            coin_table.add_row(symbol, str(s['trades']), f"[green]{s['pnl']:+.4f}[/green]")
            
    # Bottom 3 (if negative)
    for symbol, s in sorted_coins[-3:]:
        if s['pnl'] < 0 and s['trades'] > 0:
             coin_table.add_row(symbol, str(s['trades']), f"[red]{s['pnl']:+.4f}[/red]")
             
    console.print(coin_table)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("report", help="Path to JSON session report")
    args = parser.parse_args()
    analyze_session(args.report)
