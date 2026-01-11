from dataclasses import dataclass
from typing import Optional, Dict
from datetime import datetime

from .enums import SignalType

@dataclass
class RiskConfig:
    """
    Configuration for Risk Manager.
    """
    # Position Sizing
    sizing_method: str = "fixed_fraction"  # fixed_fraction, kelly, half_kelly
    risk_per_trade_pct: float = 0.01       # 1% per trade default
    max_position_size_pct: float = 1.0     # Cap at 100% of equity (no leverage by default)
    
    # Stops / targets
    default_stop_atr_mult: float = 2.0
    default_target_atr_mult: float = 3.0
    min_risk_reward_ratio: float = 1.5
    
    # Global Limits
    max_open_positions: int = 5
    max_daily_loss_pct: float = 0.05
    max_leverage: float = 3.0

    # Kelly specific
    kelly_win_rate: float = 0.5  # Historical win rate guess
    kelly_avg_win: float = 2.0   # Avg Win / Avg Loss

class RiskManager:
    """
    Centralized Risk Management Module.
    
    Enforces:
    1. Position Sizing
    2. Global Risk Limits
    3. Stop Loss / Take Profit Calculation
    """
    
    def __init__(self, config: RiskConfig):
        self.config = config
        self.daily_pnl = 0.0
        self.daily_loss_limit_hit = False
        self.current_open_positions = 0
        self.last_reset_date = None

    def check_new_entry(self, current_equity: float, active_positions: int) -> bool:
        """
        Global gatekeeper for new entries.
        """
        # Daily Reset Logic
        today = datetime.now().date() # Note: In simulation utilize engine time if possible, but for now simple check
        if self.last_reset_date != today:
            self.daily_pnl = 0.0
            self.daily_loss_limit_hit = False
            self.last_reset_date = today

        if self.daily_loss_limit_hit:
            return False

        if active_positions >= self.config.max_open_positions:
            return False
            
        return True

    def calculate_position_size(self, current_equity: float, entry_price: float, 
                              stop_loss_price: float) -> float:
        """
        Calculate position size in BASE currency (e.g. BTC amount).
        """
        if entry_price <= 0:
            return 0.0
            
        risk_per_share = abs(entry_price - stop_loss_price)
        if risk_per_share == 0:
            return 0.0

        # Method: Fixed Fraction
        if self.config.sizing_method == "fixed_fraction":
            risk_amount = current_equity * self.config.risk_per_trade_pct
            size = risk_amount / risk_per_share
        
        # Method: Kelly / Half-Kelly
        elif "kelly" in self.config.sizing_method:
            win_rate = self.config.kelly_win_rate
            win_loss_ratio = self.config.kelly_avg_win
            
            # Kelly Formula: f = p - q/b where p=win_rate, q=1-p, b=win_loss_ratio
            kelly_pct = win_rate - (1 - win_rate) / win_loss_ratio
            
            if self.config.sizing_method == "half_kelly":
                kelly_pct = kelly_pct / 2
            
            # Cap negative Kelly (don't trade) and excessive Kelly
            kelly_pct = max(0.0, min(kelly_pct, 0.2)) # Hard cap 20% for safety
            
            size_usd = current_equity * kelly_pct
            size = size_usd / entry_price
        else:
            # Default fallback
            size = (current_equity * 0.01) / risk_per_share

        # Apply Max Position Size Cap
        max_size_usd = current_equity * self.config.max_position_size_pct * self.config.max_leverage
        if (size * entry_price) > max_size_usd:
            size = max_size_usd / entry_price

        # Round down to 8 decimals to avoid precision errors
        import math
        factor = 10**8
        size = math.floor(size * factor) / factor

        return size

    def update_daily_pnl(self, pnl: float):
        """
        Update daily PL and check max loss limit.
        """
        self.daily_pnl += pnl
        # Assuming we track equity start of day elsewhere, but simple percentage check:
        # If we don't have start_of_day_equity, we might need to approximate or pass it in.
        # For now, we'll just track PnL. To enforce % max loss we need base.
        pass # Todo: Refine this with actual equity tracking

    def fail_daily_check(self, start_of_day_equity: float):
        if self.daily_pnl < -(start_of_day_equity * self.config.max_daily_loss_pct):
            self.daily_loss_limit_hit = True
