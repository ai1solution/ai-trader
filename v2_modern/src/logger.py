import csv
import logging
from typing import Optional, Dict

logger = logging.getLogger("Trajectory")

class TrajectoryLogger:
    HEADERS = [
        "Timestamp_IST", "Symbol", "State", "Regime", 
        "Velocity", "Entry_Vel", "Decay", "Heat", "EQS", 
        "Action", "Message", "Price", "MFE", "Exit_Reason",
        "Open", "High", "Low", "Close", "Volume"
    ]

    def __init__(self, file_path="trajectory.csv"):
        self.file_path = file_path
        self._init_file()

    def _init_file(self):
        try:
            with open(self.file_path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(self.HEADERS)
        except Exception as e:
            logger.error(f"Failed to init trajectory file: {e}")

    def log_tick(self, timestamp_str: str, bs_data: Dict):
        """
        Logs a single tick/row to the CSV.
        bs_data expects keys matching the log logic:
        symbol, state, regime, velocity, entry_vel, action, msg, price, ohlcv, etc.
        """
        try:
            ohlcv = bs_data.get('ohlcv', {})
            o = ohlcv.get('o', 0)
            h = ohlcv.get('h', 0)
            l = ohlcv.get('l', 0)
            c = ohlcv.get('c', 0)
            v = ohlcv.get('v', 0)
            
            row = [
                timestamp_str,
                bs_data.get('symbol'),
                bs_data.get('state'),
                bs_data.get('regime'),
                f"{bs_data.get('velocity', 0):.4f}",
                f"{bs_data.get('entry_vel', 0):.4f}",
                0, # Decay (removed/unused)
                0, # Heat
                0, # EQS
                bs_data.get('action'),
                bs_data.get('msg'),
                f"{bs_data.get('price', 0):.8f}",
                0, # MFE
                "", # Exit Reason
                o, h, l, c, v
            ]
            
            with open(self.file_path, 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(row)
        except Exception as e:
            logger.error(f"Trajectory log error: {e}")
