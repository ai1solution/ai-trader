"""
Shared Capital Portfolio Manager.
Manages global equity, allocations, and risk limits.
"""
from typing import Dict, Optional
from collections import defaultdict
from datetime import datetime

class Portfolio:
    def __init__(self, initial_capital: float = 10000.0, max_drawdown_pct: float = 0.10):
        self.initial_capital = initial_capital
        self.current_capital = initial_capital # Cash + Realized PnL
        self.max_drawdown_pct = max_drawdown_pct
        
        self.allocations: Dict[str, float] = defaultdict(float) # symbol -> amount
        self.strategy_allocations: Dict[str, float] = defaultdict(float) # strategy -> amount
        
        self.max_per_symbol_pct = 0.20
        self.max_per_strategy_pct = 0.60
        
        self.daily_start_equity = initial_capital
        self.current_date: Optional[str] = None
        
        # Stats
        self.peak_equity = initial_capital

    def update_time(self, timestamp: datetime):
        """
        Check for new day to reset daily tracking.
        """
        date_str = timestamp.strftime("%Y-%m-%d")
        if self.current_date != date_str:
            # New Day
            self.current_date = date_str
            self.daily_start_equity = self.current_capital # Approximated, ideally includes unrealized
            # Reset daily counters if any
            
    def request_allocation(self, symbol: str, strategy: str, amount: float) -> float:
        """
        Request capital for a trade.
        Returns amount allocated (0 if rejected).
        """
        # 1. Drawdown Check
        # Drawdown from Peak
        dd = (self.peak_equity - self.current_capital) / self.peak_equity
        if dd > self.max_drawdown_pct:
            return 0.0
            
        # Daily Drawdown Check (from start of day)
        daily_dd = (self.daily_start_equity - self.current_capital) / self.daily_start_equity
        if daily_dd > (self.max_drawdown_pct / 2): # Stricter daily limit?
             pass # For now, just global DD logic
             
        # 2. Availability Check
        used = sum(self.allocations.values())
        free = self.current_capital - used
        
        if amount > free:
            return 0.0
            
        # 3. Limits
        # Symbol Gap
        current_sym_exposure = self.allocations[symbol]
        if (current_sym_exposure + amount) > (self.current_capital * self.max_per_symbol_pct):
            return 0.0
            
        # Strategy Gap
        current_strat_exposure = self.strategy_allocations[strategy]
        if (current_strat_exposure + amount) > (self.current_capital * self.max_per_strategy_pct):
            return 0.0
            
        # Approved
        self.allocations[symbol] += amount
        self.strategy_allocations[strategy] += amount
        return amount

    def release_allocation(self, symbol: str, strategy: str, original_amount: float, pnl: float):
        """
        Return capital + PnL to pool.
        """
        self.allocations[symbol] -= original_amount
        self.strategy_allocations[strategy] -= original_amount
        
        # Fix float precision drift
        if self.allocations[symbol] < 1e-9: self.allocations[symbol] = 0.0
        if self.strategy_allocations[strategy] < 1e-9: self.strategy_allocations[strategy] = 0.0
        
        self.current_capital += pnl
        self.peak_equity = max(self.peak_equity, self.current_capital)
        
    def get_equity(self) -> float:
        return self.current_capital
