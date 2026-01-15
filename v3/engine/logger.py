"""
Structured logging for the trading engine.

Every decision is logged with full context:
- symbol, state, event, reason
- velocity, regime, price
- entry/exit prices, PnL

Logs are JSON lines for easy parsing and analysis.
"""

import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from pathlib import Path

from .enums import TradingState, Regime, ExitReason
from ..utils import format_price_str


class EngineLogger:
    """
    Structured logger for trading decisions.
    
    Writes to both file (JSON lines) and console (human-readable).
    Supports partial disabling (no file) by passing log_file=None.
    """
    
    def __init__(self, log_file: Optional[str] = "logs/engine.log", log_level: str = "INFO"):
        """
        Initialize logger.
        
        Args:
            log_file: Path to log file, or None to disable file logging
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        """
        self.log_file = log_file
        self.json_file = None
        
        # Only set up file logging if a path is provided
        if self.log_file:
            # Create log directory if needed
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Open JSON log file
            self.json_file = open(log_file, 'a', encoding='utf-8')
        
        # Set up Python logger for console
        self.console_logger = logging.getLogger("TradingEngine")
        self.console_logger.setLevel(getattr(logging, log_level.upper()))
        
        # Console handler (human-readable)
        if not self.console_logger.handlers:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(getattr(logging, log_level.upper()))
            formatter = logging.Formatter(
                '%(asctime)s [%(levelname)s] %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            console_handler.setFormatter(formatter)
            self.console_logger.addHandler(console_handler)
            
    def log_info(self, message: str):
        """Log an informational message."""
        self.console_logger.info(message)
        if self.json_file:
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "event": "INFO",
                "message": message
            }
            json_line = json.dumps(log_entry)
            self.json_file.write(json_line + '\n')
            self.json_file.flush()
        
    def log_decision(self, 
                    timestamp: datetime,
                    symbol: str,
                    state: TradingState,
                    event: str,
                    reason: Optional[str] = None,
                    velocity: Optional[float] = None,
                    regime: Optional[Regime] = None,
                    price: Optional[float] = None,
                    **kwargs):
        """
        Log a trading decision.
        """
        # Build log entry
        log_entry = {
            "timestamp": timestamp.isoformat(),
            "symbol": symbol,
            "state": state.name,
            "event": event,
        }
        
        # Add optional fields
        if reason is not None:
            log_entry["reason"] = reason
        if velocity is not None:
            log_entry["velocity"] = round(velocity, 6)
        if regime is not None:
            log_entry["regime"] = regime.name
        if price is not None:
            log_entry["price"] = round(price, 2)
            
        # Add extra kwargs
        for key, value in kwargs.items():
            if value is not None:
                # Round floats for readability
                if isinstance(value, float):
                    log_entry[key] = round(value, 6)
                elif isinstance(value, (ExitReason,)):
                    log_entry[key] = value.name
                else:
                    log_entry[key] = value
        
        # Write JSON line to file (if enabled)
        if self.json_file:
            json_line = json.dumps(log_entry)
            self.json_file.write(json_line + '\n')
            self.json_file.flush()
        
        # Write human-readable to console
        self._log_to_console(log_entry)
    
    def _log_to_console(self, log_entry: Dict[str, Any]):
        """
        Write human-readable log to console.
        """
        state = log_entry.get("state", "UNKNOWN")
        event = log_entry.get("event", "")
        reason = log_entry.get("reason", "")
        
        # Build message
        parts = [f"[{state}]", event]
        
        if reason:
            parts.append(f"| {reason}")
            
        # Add metrics
        metrics = []
        if "velocity" in log_entry:
            metrics.append(f"vel={log_entry['velocity']:.4f}")
        if "regime" in log_entry:
            metrics.append(f"regime={log_entry['regime']}")
        if "price" in log_entry:
            metrics.append(f"price={format_price_str(log_entry['price'])}")
        if "pnl" in log_entry:
            metrics.append(f"pnl={log_entry['pnl']:.2f}")
            
        if metrics:
            parts.append(f"| {' '.join(metrics)}")
            
        message = " ".join(parts)
        
        # Determine log level based on event
        if "ERROR" in event or "FAILED" in event:
            self.console_logger.error(message)
        elif "ENTRY" in event or "EXIT" in event:
            self.console_logger.warning(message)  # Use warning to highlight trades
        else:
            self.console_logger.info(message)
    
    def log_config(self, config_dict: Dict[str, Any]):
        """
        Log configuration at startup.
        """
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "event": "CONFIG_LOADED",
            "config": config_dict
        }
        
        if self.json_file:
            json_line = json.dumps(log_entry)
            self.json_file.write(json_line + '\n')
            self.json_file.flush()
        
        self.console_logger.info("Configuration loaded:")
        for key, value in config_dict.items():
            self.console_logger.info(f"  {key}: {value}")
    
    def log_replay_start(self, symbol: str, start_date: str, end_date: str, num_candles: int):
        """
        Log replay start.
        """
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "event": "REPLAY_START",
            "symbol": symbol,
            "start_date": start_date,
            "end_date": end_date,
            "num_candles": num_candles
        }
        
        if self.json_file:
            json_line = json.dumps(log_entry)
            self.json_file.write(json_line + '\n')
            self.json_file.flush()
        
        self.console_logger.warning(f"=== REPLAY START: {symbol} | {start_date} to {end_date} | {num_candles} candles ===")
    
    def log_replay_end(self, total_ticks: int, total_trades: int, duration_seconds: float):
        """
        Log replay end with stats.
        """
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "event": "REPLAY_END",
            "total_ticks": total_ticks,
            "total_trades": total_trades,
            "duration_seconds": round(duration_seconds, 2)
        }
        
        if self.json_file:
            json_line = json.dumps(log_entry)
            self.json_file.write(json_line + '\n')
            self.json_file.flush()
        
        self.console_logger.warning(f"=== REPLAY END: {total_trades} trades | {total_ticks} ticks | {duration_seconds:.2f}s ===")
    
    def close(self):
        """Close log file."""
        if self.json_file:
            self.json_file.close()
            self.json_file = None
    
    def __del__(self):
        """Ensure file is closed."""
        self.close()


    def log_trade(self, trade_dict: Dict[str, Any]):
        """
        Log a completed trade to CSV.
        """
        import csv
        import os
        
        # Ensure results directory exists
        os.makedirs("results", exist_ok=True)
        file_path = "results/trades.csv"
        file_exists = os.path.isfile(file_path)
        
        with open(file_path, "a", newline='') as f:
            writer = csv.writer(f)
            # Write header if new file
            if not file_exists:
                writer.writerow(["Timestamp", "Symbol", "Direction", "Entry Price", "Exit Price", "PnL", "Reason", "Duration"])
            
            # Extract fields with safe defaults
            timestamp = datetime.now().isoformat()
            symbol = trade_dict.get("symbol", "UNKNOWN")
            direction = trade_dict.get("direction", "UNKNOWN")
            entry = trade_dict.get("entry_price", 0.0)
            exit_price = trade_dict.get("exit_price", 0.0)
            pnl = trade_dict.get("net_pnl", 0.0)
            reason = trade_dict.get("reason", "UNKNOWN")
            duration = trade_dict.get("duration", 0)
            
            writer.writerow([timestamp, symbol, direction, f"{entry:.8f}", f"{exit_price:.8f}", f"{pnl:.8f}", reason, duration])

# Convenience function for simple logging
def log_decision(**kwargs):
    """
    Convenience function for logging decisions.
    
    Creates a one-off logger (not recommended for production).
    Use EngineLogger instance for better performance.
    """
    logger = EngineLogger()
    logger.log_decision(**kwargs)
    logger.close()
