"""
Live mock trading CLI command with interactive multi-symbol display.

Features:
- Real-time data from Binance (REST API polling)
- Multi-symbol parallel execution with threading
- Interactive rich UI with multi-panel layout
- Live statistics and position tracking
- Graceful shutdown with Ctrl+C

Usage:
    # Single symbol
    python live_mock.py --symbols BTCUSDT
    
    # Multiple symbols
    python live_mock.py --symbols BTCUSDT ETHUSDT BNBUSDT
    
    # With config overrides
    python live_mock.py --symbols BTCUSDT --arm-velocity 0.01
"""

import argparse
import sys
import threading
import signal
from pathlib import Path
from datetime import datetime
from typing import Dict, Any
from collections import defaultdict

from engine import EngineConfig, TradingEngine, EngineLogger
from engine.market_data import LiveFeed
from utils import clear_logs
from rich.console import Console
from rich.live import Live
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box

console = Console()

# Global control flag
running = True


def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully."""
    global running
    running = False


class SymbolRunner:
    """Runs a single engine instance for one symbol."""
    
    def __init__(self, symbol: str, config: EngineConfig):
        self.symbol = symbol
        self.config = config
        self.stats = {}
        self.error = None
        self.tick_count = 0
        self.current_price = 0.0
        self.current_state = "INIT"
        self.velocity = 0.0
        self.position_pnl = 0.0
        self.is_in_position = False
        
    def run(self):
        """Run the engine in a loop until stopped."""
        global running
        
        try:
            # Create logger for this symbol
            log_file = Path(f"logs/{self.symbol}.log")
            logger = EngineLogger(log_file=log_file, log_level=self.config.log_level)
            
            # Create live feed
            feed = LiveFeed(self.symbol, exchange="binance", poll_interval=2.0)
            
            # Create engine
            engine = TradingEngine(self.symbol, self.config, logger)
            
            # Run loop
            while running and feed.has_more_data():
                tick = feed.get_next_tick()
                
                if tick is None:
                    continue
                
                # Process tick
                engine.on_tick(tick)
                
                # Update display stats
                self.tick_count += 1
                self.current_price = tick.price
                self.current_state = engine.state_machine.get_state().name
                self.is_in_position = (engine.position is not None)
                
                # Get velocity if available
                if hasattr(engine.strategy, 'velocities') and len(engine.strategy.velocities) > 0:
                    self.velocity = engine.strategy.velocities[-1]
                
                # Get position PnL if in position
                if engine.position:
                    self.position_pnl = engine.position.get_pnl(tick.price)
                else:
                    self.position_pnl = 0.0
                
                # Get statistics
                self.stats = engine.get_statistics()
            
            # Stop feed
            feed.stop()
            logger.close()
            
        except Exception as e:
            self.error = str(e)


def create_symbol_panel(symbol: str, runner: SymbolRunner) -> Panel:
    """Create a panel for a single symbol."""
    
    if runner.error:
        content = Text(f"ERROR: {runner.error}", style="red bold")
        return Panel(content, title=f"[red]{symbol}[/red]", border_style="red")
    
    # Create table
    table = Table(show_header=False, box=None, padding=(0, 1))
    table.add_column("Key", style="cyan", width=18)
    table.add_column("Value", style="white")
    
    # Price
    price_style = "green" if runner.tick_count > 0 else "yellow"
    table.add_row("Price", f"[{price_style}]${runner.current_price:,.2f}[/{price_style}]")
    
    # State
    state_colors = {
        "WAIT": "white",
        "ARM": "yellow",
        "ENTRY": "green",
        "HOLD": "blue",
        "EXIT": "red",
        "COOLDOWN": "magenta"
    }
    state_color = state_colors.get(runner.current_state, "white")
    table.add_row("State", f"[{state_color}]{runner.current_state}[/{state_color}]")
    
    # Velocity
    vel_color = "green" if runner.velocity > 0 else "red" if runner.velocity < 0 else "white"
    table.add_row("Velocity", f"[{vel_color}]{runner.velocity*100:+.3f}%[/{vel_color}]")
    
    # Position
    if runner.is_in_position:
        pnl_color = "green" if runner.position_pnl >= 0 else "red"
        table.add_row("Position PnL", f"[{pnl_color}]${runner.position_pnl:+,.2f}[/{pnl_color}]")
    else:
        table.add_row("Position", "[dim]No position[/dim]")
    
    # Trades
    trades = runner.stats.get('total_trades', 0)
    wins = runner.stats.get('winning_trades', 0)
    losses = runner.stats.get('losing_trades', 0)
    table.add_row("Trades", f"{trades} ({wins}W/{losses}L)")
    
    # Total PnL
    total_pnl = runner.stats.get('total_pnl', 0.0)
    pnl_color = "green" if total_pnl >= 0 else "red"
    table.add_row("Total PnL", f"[{pnl_color}]${total_pnl:+,.2f}[/{pnl_color}]")
    
    # Ticks
    table.add_row("Ticks", f"{runner.tick_count:,}")
    
    # Create panel
    border_color = "green" if runner.is_in_position else "blue"
    return Panel(table, title=f"[bold]{symbol}[/bold]", border_style=border_color, box=box.ROUNDED)


def create_header_panel(runners: Dict[str, SymbolRunner], start_time: datetime) -> Panel:
    """Create aggregated header panel."""
    
    # Calculate aggregated stats
    total_trades = sum(r.stats.get('total_trades', 0) for r in runners.values())
    total_pnl = sum(r.stats.get('total_pnl', 0.0) for r in runners.values())
    active_positions = sum(1 for r in runners.values() if r.is_in_position)
    unrealized_pnl = sum(r.position_pnl for r in runners.values())
    
    # Runtime
    runtime = (datetime.now() - start_time).total_seconds()
    runtime_str = f"{int(runtime // 60)}m {int(runtime % 60)}s"
    
    # Create content
    table = Table(show_header=False, box=None, expand=True)
    table.add_column("", style="cyan bold", width=20)
    table.add_column("", style="white bold", justify="right")
    table.add_column("", style="cyan bold", width=20)
    table.add_column("", style="white bold", justify="right")
    
    pnl_color = "green" if total_pnl >= 0 else "red"
    unrealized_color = "green" if unrealized_pnl >= 0 else "red"
    
    table.add_row(
        "Runtime:", runtime_str,
        "Total PnL:", f"[{pnl_color}]${total_pnl:+,.2f}[/{pnl_color}]"
    )
    table.add_row(
        "Symbols:", str(len(runners)),
        "Unrealized:", f"[{unrealized_color}]${unrealized_pnl:+,.2f}[/{unrealized_color}]"
    )
    table.add_row(
        "Active Positions:", str(active_positions),
        "Total Trades:", str(total_trades)
    )
    
    return Panel(table, title="[bold blue]LIVE MOCK TRADING - AGGREGATED STATS[/bold blue]", border_style="blue", box=box.DOUBLE)


def create_footer_panel() -> Panel:
    """Create footer panel with instructions."""
    text = Text.from_markup(
        "[dim]Press [bold]Ctrl+C[/bold] to stop and view final summary | Updates every 2 seconds[/dim]"
    )
    return Panel(text, border_style="dim", box=box.SIMPLE)


def create_layout(runners: Dict[str, SymbolRunner], start_time: datetime) -> Layout:
    """Create the full layout."""
    
    layout = Layout()
    
    # Split into header, body, footer
    layout.split_column(
        Layout(name="header", size=7),
        Layout(name="body"),
        Layout(name="footer", size=3)
    )
    
    # Set header and footer
    layout["header"].update(create_header_panel(runners, start_time))
    layout["footer"].update(create_footer_panel())
    
    # Split body into symbol panels
    num_symbols = len(runners)
    
    if num_symbols == 1:
        # Single symbol
        symbol = list(runners.keys())[0]
        layout["body"].update(create_symbol_panel(symbol, runners[symbol]))
    elif num_symbols == 2:
        # Two columns
        layout["body"].split_row(
            Layout(name="col1"),
            Layout(name="col2")
        )
        symbols = list(runners.keys())
        layout["body"]["col1"].update(create_symbol_panel(symbols[0], runners[symbols[0]]))
        layout["body"]["col2"].update(create_symbol_panel(symbols[1], runners[symbols[1]]))
    else:
        # Grid layout (2 columns, multiple rows)
        symbols = list(runners.keys())
        num_rows = (num_symbols + 1) // 2
        
        rows = []
        for i in range(num_rows):
            rows.append(Layout(name=f"row{i}"))
        
        layout["body"].split_column(*rows)
        
        for i, row_layout in enumerate(rows):
            left_idx = i * 2
            right_idx = left_idx + 1
            
            if right_idx < num_symbols:
                # Two columns
                row_layout.split_row(
                    Layout(name=f"col{left_idx}"),
                    Layout(name=f"col{right_idx}")
                )
                row_layout[f"col{left_idx}"].update(create_symbol_panel(symbols[left_idx], runners[symbols[left_idx]]))
                row_layout[f"col{right_idx}"].update(create_symbol_panel(symbols[right_idx], runners[symbols[right_idx]]))
            else:
                # Single column (odd number)
                row_layout.update(create_symbol_panel(symbols[left_idx], runners[symbols[left_idx]]))
    
    return layout


def main():
    """Main entry point for live mock command."""
    global running
    
    parser = argparse.ArgumentParser(
        description="Live Mock Trading - Real-Time Multi-Symbol Execution",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Single symbol live trading
  python live_mock.py --symbols BTCUSDT
  
  # Multi-symbol live trading
  python live_mock.py --symbols BTCUSDT ETHUSDT BNBUSDT
  
  # With config overrides
  python live_mock.py --symbols BTCUSDT --arm-velocity 0.01
        """
    )
    
    # Required arguments
    parser.add_argument(
        '--symbols',
        nargs='+',
        default=['BTCUSDT'],
        help='One or more trading symbols (default: BTCUSDT)'
    )
    
    # Config overrides
    parser.add_argument('--arm-velocity', type=float, help='ARM velocity threshold (default: 0.005)')
    parser.add_argument('--arm-persistence', type=int, help='ARM persistence ticks (default: 5)')
    parser.add_argument('--atr-stop', type=float, help='ATR stop multiplier (default: 2.0)')
    parser.add_argument('--trailing-stop', type=float, help='Trailing stop %% (default: 0.02)')
    parser.add_argument('--log-level', type=str, choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], default='INFO')
    parser.add_argument('--no-clear-logs', action='store_true', help='Do not clear logs before run')
    
    args = parser.parse_args()
    
    # Setup signal handler
    signal.signal(signal.SIGINT, signal_handler)
    
    # Clear logs
    if not args.no_clear_logs:
        clear_logs(Path("logs"))
    
    # Create config
    config = EngineConfig(
        arm_velocity_threshold=args.arm_velocity or 0.005,
        arm_persistence_ticks=args.arm_persistence or 5,
        atr_stop_multiplier=args.atr_stop or 2.0,
        trailing_stop_pct=args.trailing_stop or 0.02,
        log_level=args.log_level,
    )
    
    # Create runners for each symbol
    runners = {symbol: SymbolRunner(symbol, config) for symbol in args.symbols}
    
    # Start threads
    threads = []
    for symbol, runner in runners.items():
        thread = threading.Thread(target=runner.run, daemon=True)
        thread.start()
        threads.append(thread)
    
    start_time = datetime.now()
    
    # Live display
    try:
        with Live(create_layout(runners, start_time), console=console, refresh_per_second=0.5) as live:
            while running and any(t.is_alive() for t in threads):
                live.update(create_layout(runners, start_time))
                import time
                time.sleep(2)
    
    except KeyboardInterrupt:
        pass
    
    # Wait for threads to finish
    running = False
    for thread in threads:
        thread.join(timeout=5)
    
    # Final summary
    console.print("\n" + "="*80, style="bold blue")
    console.print("FINAL SUMMARY", style="bold blue", justify="center")
    console.print("="*80, style="bold blue")
    console.print()
    
    summary_table = Table(show_header=True, header_style="bold cyan")
    summary_table.add_column("Symbol", style="white", width=12)
    summary_table.add_column("Trades", justify="right", style="white")
    summary_table.add_column("Win Rate", justify="right")
    summary_table.add_column("Total PnL", justify="right")
    summary_table.add_column("Best Trade", justify="right", style="green")
    summary_table.add_column("Worst Trade", justify="right", style="red")
    
    total_trades = 0
    total_pnl = 0.0
    
    for symbol, runner in sorted(runners.items()):
        stats = runner.stats
        trades = stats.get('total_trades', 0)
        win_rate = stats.get('win_rate', 0.0)
        pnl = stats.get('total_pnl', 0.0)
        best = stats.get('best_trade', 0.0)
        worst = stats.get('worst_trade', 0.0)
        
        total_trades += trades
        total_pnl += pnl
        
        pnl_style = "green" if pnl >= 0 else "red"
        
        summary_table.add_row(
            symbol,
            str(trades),
            f"{win_rate:.1f}%",
            f"[{pnl_style}]${pnl:+,.2f}[/{pnl_style}]",
            f"${best:+,.2f}",
            f"${worst:+,.2f}"
        )
    
    console.print(summary_table)
    console.print()
    
    # Overall stats
    pnl_color = "green" if total_pnl >= 0 else "red"
    console.print(f"[bold cyan]Total Trades:[/bold cyan] {total_trades}")
    console.print(f"[bold cyan]Combined PnL:[/bold cyan] [{pnl_color}]${total_pnl:+,.2f}[/{pnl_color}]")
    console.print()
    console.print(f"[cyan]Logs saved to: logs/[/cyan]")
    console.print()
    
    return 0


if __name__ == '__main__':
    try:
        exit_code = main()
        sys.exit(exit_code)
    except Exception as e:
        console.print(f"\n[red]Fatal error: {e}[/red]")
        import traceback
        traceback.print_exc()
        sys.exit(1)
