"""
State machine for trading lifecycle.

Manages state transitions with explicit rules and logging.
Updated for v4 (Strategies): logic is now largely Signal-driven.
"""

from datetime import datetime, timedelta
from typing import Optional, Tuple
from dataclasses import dataclass

from .enums import TradingState
from .config import EngineConfig

@dataclass
class StateContext:
    """
    Context information for current state.
    """
    current_state: TradingState
    
    # Timestamps
    last_update_time: Optional[datetime] = None
    state_entry_time: Optional[datetime] = None
    
    # Cooldown context
    cooldown_start_time: Optional[datetime] = None
    cooldown_duration: Optional[float] = None
    
    # Transition history
    last_transition: Optional[str] = None
    last_transition_time: Optional[datetime] = None
    
    # Legacy / Strategy-Internal fields (kept for compatibility if needed internally)
    arm_persistence_count: int = 0

class StateMachine:
    """
    Trading state machine.
    
    Generic lifecycle: WAIT -> ENTRY -> HOLD -> EXIT -> COOLDOWN -> WAIT.
    "ARM" state is deprecated/internal to strategies now.
    """
    
    def __init__(self, config: EngineConfig):
        self.config = config
        self.state = TradingState.WAIT
        self.context = StateContext(current_state=TradingState.WAIT)
        
    def get_state(self) -> TradingState:
        return self.state
        
    def update(self, current_time: datetime, is_in_position: bool) -> Tuple[TradingState, Optional[str]]:
        """
        Update state machine based on current conditions.
        """
        self.context.last_update_time = current_time
        
        # Check transitions based on current state
        if self.state == TradingState.WAIT:
            self._update_wait(current_time)
            
        elif self.state == TradingState.ARM:
            # Legacy fallback
            self._transition(TradingState.WAIT, "arm_deprecated", current_time)
            
        elif self.state == TradingState.ENTRY:
            self._update_entry(is_in_position)
            
        elif self.state == TradingState.HOLD:
            pass # HOLD transitions driven by Engine/Strategy exits
            
        elif self.state == TradingState.EXIT:
            self._update_exit(current_time)
            
        elif self.state == TradingState.COOLDOWN:
            self._update_cooldown(current_time)
            
        return self.state, self.context.last_transition

    def _update_wait(self, current_time: datetime):
        """Passive WAIT state."""
        pass
        
    def _update_entry(self, is_in_position: bool):
        """ENTRY -> HOLD if position confirmed."""
        if is_in_position:
            self._transition(TradingState.HOLD, "position_confirmed", current_time)

    def _update_exit(self, current_time: datetime):
        """EXIT -> COOLDOWN immediately."""
        self._transition(TradingState.COOLDOWN, "exit_complete", current_time)

    def _update_cooldown(self, current_time: datetime):
        """COOLDOWN -> WAIT after duration."""
        if self.context.cooldown_start_time is None:
            self.context.cooldown_start_time = current_time
            
        # Default duration if not set
        if self.context.cooldown_duration is None:
             self.context.cooldown_duration = self.config.cooldown_duration_seconds
            
        elapsed = (current_time - self.context.cooldown_start_time).total_seconds()
        
        if elapsed >= self.context.cooldown_duration:
            self._transition(TradingState.WAIT, "cooldown_complete", current_time)
            self._reset_cooldown()

    # --- External Triggers ---

    def request_entry(self, current_time: datetime) -> bool:
        """
        Request transition to ENTRY state.
        Returns True if allowed (e.g. from WAIT), False otherwise.
        """
        if self.state == TradingState.WAIT:
            self._transition(TradingState.ENTRY, "strategy_signal", current_time)
            return True
        return False
        
    def force_exit(self, current_time: datetime, reason: str):
        """Force transition to EXIT."""
        # Only if we are in HOLD or ENTRY
        if self.state in [TradingState.HOLD, TradingState.ENTRY]:
            self._transition(TradingState.EXIT, reason, current_time)
            
    def set_position_entry(self, price: float, time: datetime):
        """Record entry (called by engine)."""
        # If in ENTRY, we move to HOLD automatically in update() or here?
        # Let's ensure strict state.
        if self.state == TradingState.ENTRY:
            self._transition(TradingState.HOLD, "position_filled", time)

    def set_cooldown_duration(self, duration: float):
        """Set dynamic cooldown duration."""
        self.context.cooldown_duration = duration

    # --- Internal helpers ---

    def _transition(self, new_state: TradingState, reason: str, current_time: datetime):
        """Execute state transition."""
        if new_state != self.state:
            self.context.last_transition = reason
            self.context.last_transition_time = current_time
            self.state = new_state
            self.context.state_entry_time = current_time
            
    def _reset_cooldown(self):
        self.context.cooldown_start_time = None
        self.context.cooldown_duration = None

    def get_context_summary(self):
        return {
            "state": self.state.name,
            "last_transition": self.context.last_transition,
            "cooldown_remaining": 0 # Todo calculation
        }
