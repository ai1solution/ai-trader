import logging
import sys
from rich.console import Console
from rich.logging import RichHandler

console = Console()

def setup_logging(log_file="engine.log", component_name="Engine"):
    """
    Sets up logging to both console (Rich) and file.
    """
    # Remove existing handlers to avoid duplicates during re-runs
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)

    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[
            RichHandler(console=console, rich_tracebacks=True, show_path=False),
            logging.FileHandler(log_file)
        ]
    )
    logger = logging.getLogger(component_name)
    return logger

def format_price(price):
    """
    Smart auto-formatting for crypto prices.
    e.g. BTC -> 2 decimals, PEPE -> 8 decimals
    """
    if price is None: return "N/A"
    if price > 1000:
        return f"{price:,.2f}"
    elif price > 1:
        return f"{price:,.4f}"
    else:
        return f"{price:.8f}"

def color_text(text, color):
    # Fallback if rich not used directly in string
    return f"[{color}]{text}[/{color}]"
