import sys
import math
from collections import deque
from typing import Optional, List, Dict, Any, Deque
from datetime import datetime

from .config import EngineConfig
from .enums import TradingState, ExitReason, SignalType, Regime
from .state import StateMachine
from .market_data import Tick
from .logger import EngineLogger
from .risk import RiskManager
from .strategy import Signal, Strategy
from . import strategies

# Map strategy names to classes
STRATEGY_MAP = {
    "momentum": strategies.MomentumStrategy,
    "mean_reversion": strategies.MeanReversionStrategy,
    "trend_follow": strategies.TrendFollowingStrategy,
    "breakout": strategies.BreakoutStrategy,
    "scalping": strategies.ScalpingStrategy
}

class Position:
    """
    Current position state.
    
    Tracks entry price, stop loss, trailing stop, PnL.
    """
    def __init__(self, entry_price: float, entry_time: datetime, 
                 size_usd: float, direction: SignalType, size_asset: float = 0.0):
        self.entry_price = entry_price
        self.entry_time = entry_time
        self.size_usd = size_usd  # Initial size in USD
        self.size_asset = size_asset # Size in Asset (e.g. BTC)
        self.direction = direction
        
        self.stop_loss_price: float = 0.0
        self.take_profit_price: Optional[float] = None
        self.trailing_stop_price: Optional[float] = None
        self.highest_price = entry_price # For MFE tracking
        self.lowest_price = entry_price
        
        # Current state
        self.current_pnl = 0.0
        self.unrealized_pnl = 0.0
        
        # MFE/Partial Logic
        self.partial_taken = False
        self.partial_realized_pnl = 0.0
        self.remaining_size = 1.0 # Fraction remaining (1.0 = 100%)
        
        self._post_partial_trail_active = False # Internal flag

    def update_trailing_stop(self, current_price: float, trail_pct: float):
        """
        Update trailing stop (monotonic).
        """
        # Update MFE
        if current_price > self.highest_price:
            self.highest_price = current_price
        if current_price < self.lowest_price:
            self.lowest_price = current_price
            
        if trail_pct <= 0:
            return

        # Calculate potential new stop
        if self.direction == SignalType.LONG:
            potential_stop = current_price * (1.0 - trail_pct)
            # Only move UP
            if self.trailing_stop_price is None or potential_stop > self.trailing_stop_price:
                self.trailing_stop_price = round(potential_stop, 8)
                
        elif self.direction == SignalType.SHORT:
            potential_stop = current_price * (1.0 + trail_pct)
            # Only move DOWN
            if self.trailing_stop_price is None or potential_stop < self.trailing_stop_price:
                self.trailing_stop_price = round(potential_stop, 8)

    def get_pnl(self, current_price: float) -> float:
        """
        Calculate total PnL (size-weighted).
        """
        # Calculate unrealized PnL on remaining portion
        price_diff = 0.0
        if self.direction == SignalType.LONG:
            price_diff = current_price - self.entry_price
        else:
            price_diff = self.entry_price - current_price
            
        # PnL = (Price Diff / Entry Price) * Position Size USD * Remaining Fraction
        if self.entry_price > 0:
            pct_change = price_diff / self.entry_price
            unrealized = pct_change * self.size_usd * self.remaining_size
        else:
            unrealized = 0.0
            
        return self.partial_realized_pnl + unrealized

    def check_partial_trigger(self, current_price: float, trigger_pct: float) -> bool:
        """
        Check if partial profit should trigger based on MFE.
        """
        if self.entry_price == 0:
            return False
            
        mfe_pct = 0.0
        if self.direction == SignalType.LONG:
            # High - Entry
            mfe_pct = (self.highest_price - self.entry_price) / self.entry_price
        else:
            # Entry - Low
            mfe_pct = (self.entry_price - self.lowest_price) / self.entry_price
            
        return mfe_pct >= trigger_pct

    def execute_partial(self, current_price: float, close_ratio: float, 
                       current_time: datetime) -> float:
        """
        Execute partial profit exit.
        """
        # 1. Calculate PnL on the portion being closed
        # Note: We close 'close_ratio' of the REMAINING size?
        # Usually partial is % of ORIGINAL size. Let's assume % of current.
        # But standard is usually 50% of position.
        
        fraction_to_close = self.remaining_size * close_ratio
        
        # Calculate PnL for this fraction
        price_diff = 0.0
        if self.direction == SignalType.LONG:
            price_diff = current_price - self.entry_price
        else:
            price_diff = self.entry_price - current_price
            
        pct_change = price_diff / self.entry_price
        pct_change = price_diff / self.entry_price
        realized_pnl = round(pct_change * self.size_usd * fraction_to_close, 8)
        
        # Update state
        self.partial_realized_pnl += realized_pnl
        self.remaining_size -= fraction_to_close
        self.partial_taken = True
        
        return realized_pnl

    def update_stop_after_partial(self, buffer_pct: float):
        """
        Update stop-loss after partial exit (monotonic + safety).
        """
        # Move stop to Entry +/- Buffer
        new_stop = 0.0
        if self.direction == SignalType.LONG:
            new_stop = self.entry_price * (1.0 + buffer_pct)
            # Ensure we don't move stop DOWN if it's already higher
            if new_stop > self.stop_loss_price:
                self.stop_loss_price = round(new_stop, 8)
                # Also reset trailing stop if it's below new stop
                if self.trailing_stop_price and self.trailing_stop_price < new_stop:
                    self.trailing_stop_price = round(new_stop, 8)
                    
        else:
            new_stop = self.entry_price * (1.0 - buffer_pct)
            if new_stop < self.stop_loss_price:
                 self.stop_loss_price = round(new_stop, 8)
                 if self.trailing_stop_price and self.trailing_stop_price > new_stop:
                    self.trailing_stop_price = round(new_stop, 8)


class TradingEngine:
    """
    Core trading engine.
    
    Processes ticks, updates indicators, manages state, executes trades.
    Now supports pluggable Strategies and Risk Management.
    """
    
    def __init__(self, symbol: str, config: EngineConfig, logger: EngineLogger):
        self.symbol = symbol
        self.config = config
        self.logger = logger
        
        # Risk Manager
        self.risk_manager = RiskManager(config.risk)
        
        # Strategy Initialization
        strategy_class = STRATEGY_MAP.get(config.active_strategy, strategies.momentum.MomentumStrategy)
        # Pass merged config (EngineConfig contains strategy params often, or we pass dict)
        # Strategy expects 'config' object or dict.
        self.strategy: Strategy = strategy_class(config)
        self.logger.log_info(f"Initialized Strategy: {self.strategy.name}")
        
        # State machine
        self.state_machine = StateMachine(config)
        
        # Position tracking
        self.position: Optional[Position] = None
        
        # Statistics
        self.tick_count = 0
        self.trade_count = 0
        
        # PnL tracking
        self.trade_pnls: List[float] = [] 
        self.total_pnl = 0.0
        self.winning_trades = 0
        self.losing_trades = 0
        
        # Loser suppression tracking
        self.consecutive_stop_losses: int = 0
        self.current_cooldown_duration: float = config.cooldown_duration_seconds
        
    def on_tick(self, tick: Tick):
        """
        Process a single tick.
        """
        self.tick_count += 1
        
        # Update state machine (timers only)
        old_state = self.state_machine.get_state()
        new_state, _ = self.state_machine.update(tick.timestamp, (self.position is not None))
        
        # 1. Strategy Processing
        signal = self.strategy.on_tick(tick)
        
        # 2. Risk & Entry Logic
        # Only process entry signals if in WAIT state
        if new_state == TradingState.WAIT and signal:
             if self.risk_manager.check_new_entry(current_equity=1000, active_positions=0): # Mock equity
                 if self.state_machine.request_entry(tick.timestamp):
                     self._execute_entry(tick, signal)
        
        # 3. Position Management
        if self.position:
            # Check strategy exits
            if self.strategy.should_exit(self.position, tick):
                self.state_machine.force_exit(tick.timestamp, "strategy_exit")
                self._execute_exit(tick, "STRATEGY_EXIT")
            else:
                # Update position (Trailing stop, Partials)
                self._update_position(tick)

        # 4. Check Exit Conditions (Stop Loss, Trailing) in _update_position or separate?
        # _update_position calls _check_exit_conditions internally.
        
        pass # Completed tick

    def _execute_entry(self, tick: Tick, signal: Signal):
        """
        Execute position entry based on Signal.
        """
        # Apply Slippage
        # Buy higher, Sell lower
        slippage = tick.price * self.config.slippage_pct
        if signal.type == SignalType.LONG:
             execution_price = tick.price + slippage
        else:
             execution_price = tick.price - slippage
             
        # Calculate Size
        entry_price = execution_price
        
        # Stop loss adjustment (if it was based on raw price, might need shift, but usually strategy sets level)
        # Using Strategy's SL if available
        stop_loss = signal.stop_loss
        
        # Fallback
        if not stop_loss:
            if signal.type == SignalType.LONG:
                stop_loss = entry_price * 0.98
            else:
                stop_loss = entry_price * 1.02
        
        stop_loss = round(stop_loss, 8)
        entry_price = round(entry_price, 8)

        size_asset = self.risk_manager.calculate_position_size(
            current_equity=1000.0, 
            entry_price=entry_price,
            stop_loss_price=stop_loss
        )
        
        size_usd = size_asset * entry_price
        
        if size_usd <= 0:
            self.logger.log_info("Entry Rejected: Size 0")
            self.state_machine.force_exit(tick.timestamp, "rejected_size")
            return

        # Create Position
        self.position = Position(
            entry_price=entry_price,
            entry_time=tick.timestamp,
            size_usd=size_usd,
            size_asset=size_asset,
            direction=signal.type
        )
        self.position.stop_loss_price = stop_loss
        
        # Initialize trailing stop
        self.position.update_trailing_stop(tick.price, self.config.trailing_stop_pct)
        
        # Update State
        self.state_machine.set_position_entry(entry_price, tick.timestamp)
        
        self.trade_count += 1
        self.logger.log_decision(
            timestamp=tick.timestamp,
            symbol=self.symbol,
            state=self.state_machine.get_state(),
            event="POSITION_ENTRY",
            reason=signal.reason,
            price=tick.price,
            execution_price=entry_price,
            slippage=slippage,
            fee=size_usd * self.config.trading_fee_pct,
            stop_loss=self.position.stop_loss_price,
            direction=signal.type.name
        )

    def _update_position(self, tick: Tick):
        """
        Update open position and check exit conditions.
        """
        if self.position is None:
            return
            
        # Check partial profit trigger
        if self.config.partial_profit_enabled and not self.position.partial_taken:
            # Assuming "Trend" regime or similar. Strategy might provide regime?
            # Retain simple logic: Fixed threshold for now or config default
            threshold = self.config.partial_take_pct_trending # Default
            
            if self.position.check_partial_trigger(tick.price, threshold):
                pnl = self.position.execute_partial(tick.price, self.config.partial_close_ratio, tick.timestamp)
                self.position.update_stop_after_partial(self.config.post_partial_stop_buffer_pct)
                self.position._post_partial_trail_active = True
                
                self.logger.log_decision(
                    timestamp=tick.timestamp,
                    symbol=self.symbol,
                    state=self.state_machine.get_state(),
                    event="PARTIAL_TAKE",
                    reason="threshold_reached",
                    price=tick.price,
                    partial_realized_pnl=pnl
                )

        # Update trailing stop
        if self.position._post_partial_trail_active:
            trail = self.config.trailing_stop_pct * self.config.post_partial_trail_reduction
            self.position.update_trailing_stop(tick.price, trail)
        else:
            self.position.update_trailing_stop(tick.price, self.config.trailing_stop_pct)
            
        # Check Exits
        exit_reason = self._check_exit_conditions(tick)
        if exit_reason:
            self.state_machine.force_exit(tick.timestamp, exit_reason.name)
            self._execute_exit(tick, exit_reason.name)

    def _check_exit_conditions(self, tick: Tick) -> Optional[ExitReason]:
        if not self.position: return None
        
        # Stop Loss
        if self.position.direction == SignalType.LONG:
            if tick.price <= self.position.stop_loss_price: return ExitReason.STOP_LOSS
        else:
            if tick.price >= self.position.stop_loss_price: return ExitReason.STOP_LOSS
            
        # Trailing Stop
        if self.position.trailing_stop_price:
             if self.position.direction == SignalType.LONG:
                 if tick.price <= self.position.trailing_stop_price: return ExitReason.TRAILING_STOP
             else:
                 if tick.price >= self.position.trailing_stop_price: return ExitReason.TRAILING_STOP
                 
        return None

    def _execute_exit(self, tick: Tick, reason: str):
        if not self.position: return
        
        # Apply Slippage to Exit
        slippage = tick.price * self.config.slippage_pct
        if self.position.direction == SignalType.LONG:
             execution_price = tick.price - slippage
        else:
             execution_price = tick.price + slippage
        
        # Calculate Gross PnL
        # Note: Position.get_pnl uses 'current_price'. We should pass 'execution_price'
        gross_pnl = self.position.get_pnl(execution_price)
        
        # Calculate Fees (Entry Fee + Exit Fee)
        # Entry fee = size_usd * fee_pct
        # Exit fee = exit_value * fee_pct
        
        # Simplified: Net PnL = Gross PnL - (Total Volume * Fee Pct)
        # Total Volume = Entry Volume + Exit Volume
        total_volume = self.position.size_usd + (self.position.size_usd + gross_pnl) # Approx
        total_fees = total_volume * self.config.trading_fee_pct
        
        gross_pnl = round(gross_pnl, 8)
        total_fees = round(total_fees, 8)
        net_pnl = round(gross_pnl - total_fees, 8)
        
        self.logger.log_decision(
            timestamp=tick.timestamp,
            symbol=self.symbol,
            state=self.state_machine.get_state(),
            event="POSITION_EXIT",
            reason=reason,
            price=tick.price,
            execution_price=execution_price,
            gross_pnl=gross_pnl,
            net_pnl=net_pnl,
            fees=total_fees,
            slippage=slippage,
            direction=self.position.direction.name
        )
        
        self.trade_pnls.append(net_pnl)
        self.total_pnl += net_pnl
        if net_pnl > 0: self.winning_trades += 1
        else: self.losing_trades += 1
        
        # Log Trade to CSV
        trade_data = {
            "symbol": self.symbol,
            "direction": self.position.direction.name,
            "entry_price": self.position.entry_price,
            "exit_price": execution_price,
            "net_pnl": net_pnl,
            "reason": reason,
            "duration": (tick.timestamp - self.position.entry_time).total_seconds()
        }
        self.logger.log_trade(trade_data)
        
        # Risk Manager Update
        self.risk_manager.update_daily_pnl(net_pnl)
        if self.config.loser_suppression_enabled and reason == "STOP_LOSS":
             self.consecutive_stop_losses += 1
             # Logic for extended cooldown...
        else:
             self.consecutive_stop_losses = 0
             
        # Cooldown Logic
        if self.consecutive_stop_losses >= self.config.loser_streak_threshold:
             self.state_machine.set_cooldown_duration(self.config.cooldown_duration_seconds * self.config.extended_cooldown_multiplier)
        else:
             self.state_machine.set_cooldown_duration(self.config.cooldown_duration_seconds)
             
        self.position = None

    def get_statistics(self) -> Dict:
        win_rate = (self.winning_trades / self.trade_count * 100) if self.trade_count > 0 else 0.0
        return {
            "tick_count": self.tick_count,
            "trade_count": self.trade_count,
            "win_rate": win_rate,
            "total_pnl": self.total_pnl
        }
