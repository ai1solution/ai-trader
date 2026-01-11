"""
Trading state machine states and enums.

This module defines all type-safe enums used throughout the trading engine.
Explicit naming prevents bugs and makes state transitions auditable.
"""

from enum import Enum, auto


class TradingState(Enum):
    """
    State machine states for trading lifecycle.
    
    State flow:
    WAIT: Monitoring market, no position, no signal
    ARM: Velocity threshold crossed, accumulating confirmation
    ENTRY: ARM validated, executing entry
    HOLD: Position open, monitoring for exits
    EXIT: Exit condition triggered, closing position
    COOLDOWN: Position closed, preventing immediate re-entry
    """
    WAIT = auto()
    ARM = auto()
    ENTRY = auto()
    HOLD = auto()
    EXIT = auto()
    COOLDOWN = auto()


class SignalType(Enum):
    """
    Directional signal for velocity.
    
    LONG: Positive velocity (upward momentum)
    SHORT: Negative velocity (downward momentum)
    NEUTRAL: No clear directional bias
    """
    LONG = auto()
    SHORT = auto()
    NEUTRAL = auto()


class ExitReason(Enum):
    """
    Reasons for exiting a position.
    
    STOP_LOSS: Hard stop hit (ATR-based)
    SIGNAL_DECAY: Velocity reversed sign (momentum lost)
    TRAILING_STOP: Trailing stop triggered (price retraced)
    TIMEOUT: Holding time exceeded maximum (NOT IMPLEMENTED YET)
    """
    STOP_LOSS = auto()
    SIGNAL_DECAY = auto()
    TRAILING_STOP = auto()
    TIMEOUT = auto()  # Reserved for future use


class Regime(Enum):
    """
    Market regime classification.
    
    Used for logging/context only in v3. No entry gating.
    
    TRENDING: Directional movement with momentum
    RANGING: Sideways movement within bounds
    VOLATILE: High volatility, erratic price action
    """
    TRENDING = auto()
    RANGING = auto()
    VOLATILE = auto()
