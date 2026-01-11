import json
import logging
import os
from typing import List, Dict, Tuple
from .types import MarketRegime, SymbolData
from .config import SYMBOL_MAP, DEFAULT_CONFIG

logger = logging.getLogger("Portfolio")

class Persistence:
    def __init__(self, state_file="active_trades.json"):
        self.state_file = state_file

    def save_portfolio(self, portfolio: List[Dict]):
        try:
            with open(self.state_file, 'w') as f:
                json.dump(portfolio, f, indent=4)
        except Exception as e:
            logger.error(f"Failed to save state: {e}")

    def load_portfolio(self) -> List[Dict]:
        if not os.path.exists(self.state_file): return []
        try:
            with open(self.state_file, 'r') as f:
                return json.load(f)
        except:
            return []

class RiskManager:
    def __init__(self, config=DEFAULT_CONFIG):
        self.config = config

    def can_enter(self, symbol: str, portfolio: List[Dict], regime: MarketRegime) -> Tuple[bool, str]:
        # 1. Max Positions
        start_max = 3
        if len(portfolio) >= start_max: 
            return False, "Max Portfolio"
        
        # 2. Check for existing
        for trade in portfolio:
            if trade['symbol'] == symbol:
                return False, "Already Open"

        # 3. Regime Filter logic could go here
        return True, "OK"

    def get_effective_velocity_threshold(self, symbol: str) -> float:
        base = self.config["VELOCITY_THRESHOLD"]
        # Meme coins might need higher velocity specific logic
        if SYMBOL_MAP.get(symbol) == 'MEME':
            return base * 1.5
        return base
