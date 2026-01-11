from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum

from .market_data import Tick
from .enums import SignalType

@dataclass
class Signal:
    """
    Standardized trading signal.
    """
    type: SignalType
    symbol: str
    time: datetime
    price: float
    confidence: float = 1.0
    reason: str = ""
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None

class Strategy(ABC):
    """
    Abstract base class for all trading strategies.
    
    Responsibilities:
    1. Maintain internal state (indicators, lookback windows)
    2. Process market data (ticks/bars)
    3. Generate entry signals
    4. Advise on exits (optional, if strategy manages specific exit logic beyond standard risk)
    """
    
    def __init__(self, config: Any):
        self.config = config
        self.name = "AbstractStrategy"
    
    @abstractmethod
    def on_tick(self, tick: Tick) -> Optional[Signal]:
        """
        Process a new tick.
        return: Signal if entry condition met, else None
        """
        pass
    
    def on_bar(self, bar: Any) -> Optional[Signal]:
        """
        Process a completed candle/bar.
        Default implementation does nothing (tick-based strategies).
        """
        return None

    def get_required_indicators(self) -> List[str]:
        """
        Return list of indicator keys this strategy needs from the engine.
        or maybe the strategy calculates them internally.
        """
        return []
    
    def should_exit(self, position: Any, tick: Tick) -> bool:
        """
        Custom exit logic (e.g. indicator crossover).
        Standard stops/targets are handled by the engine/risk module,
        but strategies can force early exits.
        """
        return False
