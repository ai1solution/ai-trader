from enum import Enum, auto
from collections import deque
from dataclasses import dataclass, field
from typing import List, Optional

# --- Enums ---
class TradeState(Enum):
    WAIT = auto()
    ARM = auto()
    ENTRY = auto()
    HOLD = auto()
    EXIT = auto()
    COOLDOWN = auto()

class MarketRegime(Enum):
    TRENDING = "TRENDING"
    CHOP = "CHOP"
    LOW_VOL = "LOW_VOL"

# --- Data Classes ---
@dataclass
class SymbolData:
    symbol: str
    state: TradeState = TradeState.WAIT
    price_history: deque = field(default_factory=lambda: deque(maxlen=20))
    velocity_history: deque = field(default_factory=lambda: deque(maxlen=5))
    last_price: float = 0.0
    
    # State Tracking
    entry_price: float = 0.0
    entry_time: float = 0.0
    entry_velocity: float = 0.0
    last_trade_pnl: float = 0.0
    last_arm_time: float = 0.0
    
    def update_price(self, price: float):
        self.last_price = price
        self.price_history.append(price)

    def get_velocity(self) -> float:
        if len(self.price_history) < 2:
            return 0.0
        start = self.price_history[0]
        end = self.price_history[-1]
        if start == 0: return 0.0
        return ((end - start) / start) * 100.0
