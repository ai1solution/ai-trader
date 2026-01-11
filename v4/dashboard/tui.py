"""
Rich CLI Dashboard (v3-style).
"""
from collections import deque
from datetime import datetime, timedelta
from rich.table import Table
from rich.layout import Layout
from rich.panel import Panel
from rich.console import Console, Group
from rich.text import Text
from rich import box

class Dashboard:
    def __init__(self, runner):
        self.runner = runner
        self.console = Console()
        self.start_time = datetime.now()
        self.logs = deque(maxlen=20)
        
    def add_log(self, message: str):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.logs.append(f"[{timestamp}] {message}")
        
    def get_aggregated_stats(self):
        stats = self.runner.get_stats()
        
        total_pnl = sum(s['pnl'] for s in stats)
        total_trades = sum(s['trades'] for s in stats)
        active_positions = sum(1 for s in stats if s['active'])
        unrealized_pnl = 0.0 # Not tracked in stats yet, assuming 0 or add to runner stats later
        
        runtime = datetime.now() - self.start_time
        runtime_str = str(runtime).split('.')[0]
        
        return {
            "total_pnl": total_pnl,
            "total_trades": total_trades,
            "active_positions": active_positions,
            "runtime": runtime_str,
            "count": len(stats)
        }

    def generate_header(self) -> Panel:
        stats = self.get_aggregated_stats()
        
        table = Table(show_header=False, box=None, expand=True)
        table.add_column("Key", style="cyan bold")
        table.add_column("Value", justify="right")
        table.add_column("Key2", style="cyan bold")
        table.add_column("Value2", justify="right")
        
        pnl_color = "green" if stats['total_pnl'] >= 0 else "red"
        
        table.add_row(
            "Runtime:", stats['runtime'],
            "Total PnL:", f"[{pnl_color}]${stats['total_pnl']:+.2f}[/{pnl_color}]"
        )
        table.add_row(
            "Sorties:", str(stats['count']),
            "Active Pos:", str(stats['active_positions'])
        )
        table.add_row(
            "Total Trades:", str(stats['total_trades']),
            "Status:", "[green]RUNNING[/green]"
        )
        
        return Panel(table, title="[bold blue]AI TRADER v4 - LIVE MONITOR[/bold blue]", border_style="blue", box=box.DOUBLE)

    def generate_table(self) -> Table:
        table = Table(show_header=True, header_style="bold cyan", expand=True, box=box.ROUNDED)
        
        table.add_column("Symbol", style="white bold", width=10)
        table.add_column("Strategy", style="dim white")
        table.add_column("Price", justify="right", style="yellow")
        table.add_column("State", justify="center")
        table.add_column("Balance", justify="right")
        table.add_column("PnL", justify="right")
        table.add_column("Trades", justify="right")
        
        stats = self.runner.get_stats()
        
        for s in stats:
            pnl_style = "green" if s['pnl'] >= 0 else "red"
            state_color = "green" if s['state'] == "HOLD" else "white" if s['state'] == "WAIT" else "yellow"
            
            table.add_row(
                s['symbol'],
                s['strategy'],
                f"{s['price']:.4f}",
                f"[{state_color}]{s['state']}[/{state_color}]",
                f"${s['balance']:.2f}",
                f"[{pnl_style}]{s['pnl']:+.2f}[/{pnl_style}]",
                str(s['trades'])
            )
            
        return table

    def generate_log_panel(self) -> Panel:
        log_text = Group(*[Text.from_markup(l) for l in self.logs])
        return Panel(log_text, title="Activity Log", border_style="blue", height=15)

    def create_layout(self) -> Layout:
        layout = Layout()
        layout.split_column(
            Layout(name="header", size=6),
            Layout(name="table", ratio=1),
            Layout(name="footer", size=3)
        )
        
        layout["header"].update(self.generate_header())
        layout["table"].update(Panel(self.generate_table(), title="Active Engines", border_style="blue"))
        layout["footer"].update(Panel(Text("Press Ctrl+C to Stop", justify="center", style="dim"), box=box.SIMPLE))
        
        return layout
