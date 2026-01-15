"""
Core Trading Engine.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, Dict
import uuid

from ..common.types import Tick, OrderSide, round_price, round_qty, format_price
from ..strategies.interface import Strategy, Intent, FillEvent
from ..config.config import RiskConfig
from .regime import RegimeClassifier, MarketRegime
from .portfolio import Portfolio
from common.supabase_client import get_supabase

class TradingState:
    WAIT = "WAIT"
    ENTRY = "ENTRY" # Placing order
    HOLD = "HOLD"
    EXIT = "EXIT" # Placing exit
    COOLDOWN = "COOLDOWN"
    DISABLED = "DISABLED" # New state for expectancy protection

@dataclass
class Position:
    symbol: str
    side: OrderSide
    entry_price: float
    quantity: float
    entry_time: datetime
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    highest_price: float = 0.0 # For trailing
    lowest_price: float = 0.0

class TradingEngine:
    """
    Manages one (Symbol, Strategy) pair.
    """
    def __init__(self, symbol: str, strategy: Strategy, initial_balance: float = 100.0, 
                 risk_config: RiskConfig = None, log_queue=None, regime_classifier: RegimeClassifier = None,
                 portfolio: Portfolio = None, use_protection: bool = True, run_id: str = "offline"):
        self.symbol = symbol
        self.strategy = strategy
        self.risk_config = risk_config or {}
        self.log_queue = log_queue
        self.regime_classifier = regime_classifier
        self.portfolio = portfolio
        self.use_protection = use_protection
        self.run_id = run_id
        self.sb = get_supabase()
        
        # Initialize Balance
        # If portfolio is used, balance is ignored. 
        # If isolated (baseline), use initial_balance.
        self.balance = initial_balance if initial_balance is not None else 0.0
        
        self.state = TradingState.WAIT
        self.consecutive_losses = 0
        self.position: Optional[Position] = None
        self.trades: List[Dict] = []
        
        self.cooldown_until: Optional[datetime] = None
        self.last_tick: Optional[Tick] = None
        
        # stats
        self.total_pnl = 0.0
        self.total_pnl = 0.0
        self.win_count = 0
        self.loss_count = 0
        
    def log(self, message: str):
        if self.log_queue:
            self.log_queue.put_nowait(f"[{self.symbol}] {message}")
        else:
            print(f"[{self.symbol}] {message}")
            
        # Supabase Log
        self.sb.log_event(self.run_id, message, level="INFO", data={"symbol": self.symbol})

    async def on_tick(self, tick: Tick):
        self.last_tick = tick
        
        # 0. Cooldown check
        if self.state == TradingState.COOLDOWN:
            if tick.timestamp >= self.cooldown_until:
                self.state = TradingState.WAIT
            else:
                return

        # 1. Update Position (PnL, Trailing Stops)
        if self.state == TradingState.HOLD and self.position:
            self._update_position_valuation(tick)
            self._check_exits(tick)
        
        # 1.5 Regime Gate
        allowed = True
        current_regime = None
        if self.regime_classifier and self.state == TradingState.WAIT:
            current_regime = await self.regime_classifier.get_regime(self.symbol, tick.timestamp)
            strat_name = self.strategy.name.lower()
            
            # HARD Rules
            if "momentum" in strat_name and current_regime != MarketRegime.TRENDING:
                allowed = False
                # Optional: Log reason? Too verbose for tick
            elif "mean_reversion" in strat_name and current_regime != MarketRegime.RANGING:
                allowed = False
        
        if not allowed:
            return

        # 2. Strategy Signals
        intents = self.strategy.generate_signals(tick)
        
        # 3. Process Intents based on State
        for intent in intents:
            if self.state == TradingState.WAIT:
                 # Only process entries
                 self._handle_entry_intent(intent, tick)
            elif self.state == TradingState.HOLD:
                 # Could process explicit strategy exits here
                 if intent.side != self.position.side and intent.quantity == 0: 
                     # Opposite signal -> Exit? Or Reversal?
                     # For simplicity, treat as exit signal if configured
                     pass

    def _handle_entry_intent(self, intent: Intent, tick: Tick):
        # 1. Update Portfolio Time (Ensure daily reset matches check)
        # Assuming Runner updates portfolio time or we do it here.
        if self.portfolio:
            self.portfolio.update_time(tick.timestamp)
            
        # 2. Determine Desired Size
        # Risk Based Sizing: Risk 1% of Equity
        risk_pct = 0.01 
        sl_pct = 0.02 # Default assumption if no ATR based SL logic yet
        
        equity = self.portfolio.get_equity() if self.portfolio else 10000.0
        risk_amount = equity * risk_pct
        
        # Position Value = Risk Amount / SL%
        # e.g. 100 / 0.02 = 5000 (50% of 10k)
        # Cap at 10% of Equity for safety/diversity in 5-20 symbol universe
        desired_value = min(risk_amount / sl_pct, equity * 0.10)
        
        # 3. Request Allocation
        allocated_value = 0.0
        if self.portfolio:
            allocated_value = self.portfolio.request_allocation(self.symbol, self.strategy.name, desired_value)
        else:
            # Fallback for isolated testing
            allocated_value = self.balance
            
        if allocated_value <= 0:
            # self.log("Entry REJECTED: Insufficient Capital or Risk Limit")
            return
            
        trade_value = allocated_value
        qty = trade_value / tick.price
        
        # Slippage simulation (0.1%)
        slippage = 0.001
        fill_price = tick.price * (1 + slippage) if intent.side == OrderSide.BUY else tick.price * (1 - slippage)
        fill_price = round_price(fill_price)
        
        # Commision simulation (0.1%)
        fee = trade_value * 0.001
        
        # Create Position
        self.position = Position(
            symbol=self.symbol,
            side=intent.side,
            entry_price=fill_price,
            quantity=round_qty(qty),
            entry_time=tick.timestamp,
            stop_loss=round_price(fill_price * (1 - sl_pct) if intent.side == OrderSide.BUY else fill_price * (1 + sl_pct)), # Default 2% SL
            take_profit=self._calculate_tp(fill_price, intent.side),
            highest_price=fill_price,
            lowest_price=fill_price
        )
        
        self.state = TradingState.HOLD
        
        # Notify Strategy
        fill = FillEvent(self.symbol, intent.side, qty, fill_price, tick.timestamp, fee)
        self.strategy.on_fill(fill)
        
        self.strategy.on_fill(fill)
        
        self.log(f"ENTRY {intent.side.value} @ {fill_price:.2f} ({intent.reason})")

    
    def _calculate_tp(self, entry_price: float, side: OrderSide) -> Optional[float]:
        tp_pct = self.strategy.config.get('take_profit_pct', 0.0)
        if tp_pct <= 0:
            return None
            
        if side == OrderSide.BUY:
            return round_price(entry_price * (1 + tp_pct))
        else:
            return round_price(entry_price * (1 - tp_pct))

    def _update_position_valuation(self, tick: Tick):
        p = self.position
        if p.side == OrderSide.BUY:
            p.highest_price = max(p.highest_price, tick.price)
        else:
            p.lowest_price = min(p.lowest_price, tick.price)
            
    def _check_exits(self, tick: Tick):
        p = self.position
        reason = None
        
        # 1. Stop Loss
        if p.side == OrderSide.BUY and tick.price <= p.stop_loss:
            reason = "Stop Loss"
        elif p.side == OrderSide.SELL and tick.price >= p.stop_loss:
            reason = "Stop Loss"
            
        # 2. Take Profit (if set)
        if p.take_profit:
            if p.side == OrderSide.BUY and tick.price >= p.take_profit:
                reason = "Take Profit"
            elif p.side == OrderSide.SELL and tick.price <= p.take_profit:
                reason = "Take Profit"
        
        if reason:
            self._close_position(tick, reason)
            
    def _close_position(self, tick: Tick, reason: str):
        p = self.position
        
        # Slippage
        slippage = 0.001
        exit_price = tick.price * (1 - slippage) if p.side == OrderSide.BUY else tick.price * (1 + slippage)
        exit_price = round_price(exit_price)
        
        # Calculate PnL
        if p.side == OrderSide.BUY:
            pnl = (exit_price - p.entry_price) * p.quantity
        else:
            pnl = (p.entry_price - exit_price) * p.quantity
            
        pnl = round_price(pnl)
            
        self.total_pnl += pnl
        if pnl > 0: self.win_count += 1
        else: self.loss_count += 1
        
        # Release Allocation
        trade_value = p.entry_price * p.quantity
        if self.portfolio:
            self.portfolio.release_allocation(self.symbol, self.strategy.name, trade_value, pnl)
        else:
            self.balance += pnl
        
        self.log(f"EXIT @ {format_price(exit_price)} PnL: {pnl:.2f} ({reason})")
        
        if pnl > 0:
            self.consecutive_losses = 0
        else:
            self.consecutive_losses += 1
            
        # Logic: 2 consecutive losses -> Check Regime -> Soften to 3 or Disable
        if self.use_protection and self.consecutive_losses >= 2:
            # Check for Softening
            allow_retry = False
            if self.consecutive_losses == 2 and self.regime_classifier:
                 # ... logic (cached or previous check) ...
                 # For now, strict disable if classifier exists but we can't async check easily.
                 # Wait, if we use protection, we interpret "hits 2 stops" strictly or with softening.
                 # As per previous step implementation:
                 self.state = TradingState.DISABLED
                 self.log(f"High risk (losses={self.consecutive_losses}). Pausing strategy.")
            elif self.consecutive_losses >= 3:
                 self.state = TradingState.DISABLED
                 self.log(f"Stopped due to consecutive losses ({self.consecutive_losses}).")
        
        if self.state != TradingState.DISABLED:
            # Normal Cooldown
            self.state = TradingState.COOLDOWN
            # Cooldown 10 seconds?
            from datetime import timedelta
            self.cooldown_until = tick.timestamp + timedelta(seconds=10)
        else:
            self.position = None # Ensure clear
            
        # Log Trade
        self.trades.append({
            "entry_time": p.entry_time,
            "exit_time": tick.timestamp,
            "side": p.side.value,
            "entry_price": p.entry_price,
            "exit_price": exit_price,
            "pnl": pnl,
            "reason": reason
        })
        
        # Log Trade to CSV (Unified v3/v4 format)
        try:
            import csv
            import os
            os.makedirs("results", exist_ok=True)
            csv_file = "results/trades.csv"
            file_exists = os.path.isfile(csv_file)
            
            with open(csv_file, "a", newline='') as f:
                writer = csv.writer(f)
                if not file_exists:
                    writer.writerow(["Timestamp", "Symbol", "Direction", "Entry Price", "Exit Price", "PnL", "Reason", "Duration"])
                
                duration = (tick.timestamp - p.entry_time).total_seconds()
                writer.writerow([
                    tick.timestamp.isoformat(),
                    self.symbol,
                    p.side.value,
                    f"{p.entry_price:.8f}",
                    f"{exit_price:.8f}",
                    f"{pnl:.8f}",
                    reason,
                    duration
                ])
        except Exception as e:
            self.log(f"Failed to log trade to CSV: {e}")
            
        # Supabase Trade Log
        self.sb.log_trade(self.run_id, {
            "symbol": self.symbol,
            "side": p.side.value if hasattr(p.side, 'value') else str(p.side),
            "entry_price": p.entry_price,
            "exit_price": exit_price,
            "quantity": p.quantity,
            "pnl": pnl,
            "reason": reason,
            "entry_time": p.entry_time.isoformat(),
            "exit_time": tick.timestamp.isoformat()
        })
        

