"""
Configuration parameters for the trading engine.

Single source of truth for all tunable parameters.
All values here should be treated as constants during a run.
"""

from dataclasses import dataclass, field
from typing import Dict, Any

from .risk import RiskConfig

@dataclass(frozen=True)
class EngineConfig:
    """
    Core trading engine configuration.
    
    All parameters are frozen to prevent accidental modification during runtime.
    """
    
    # Strategy & Risk
    active_strategy: str = "momentum"  # momentum, mean_reversion, trend_follow, breakout
    strategy_params: Dict[str, Any] = field(default_factory=dict)
    
    # Risk Config
    # Uses default factory to avoid mutable default argument
    risk: RiskConfig = field(default_factory=RiskConfig)
    
    # === ARM (Alert/Ready/Monitor) Configuration ===
    arm_velocity_threshold: float = 0.005
    arm_persistence_ticks: int = 5
    arm_timeout_seconds: float = 30.0
    velocity_lookback_ticks: int = 15
    acceleration_window_ticks: int = 3
    
    # === Trading Cost Simulation ===
    # Trading fee percentage per order (e.g., 0.001 = 0.1% Binance default)
    trading_fee_pct: float = 0.001
    
    # Slippage percentage per order (e.g., 0.0005 = 0.05%)
    # Simulates worse execution price due to latency/spread
    slippage_pct: float = 0.0005
    
    # === Position Sizing ===
    position_size_usd: float = 1000.0
    
    # === Risk Management ===
    atr_stop_multiplier: float = 2.0
    atr_period_ticks: int = 30
    trailing_stop_pct: float = 0.02
    
    # === Exit Conditions ===
    signal_decay_enabled: bool = True
    
    # === Partial Profit-Taking ===
    partial_profit_enabled: bool = True
    partial_take_pct: float = 0.006
    partial_take_pct_trending: float = 0.0045
    partial_take_pct_ranging: float = 0.0075
    partial_close_ratio: float = 0.5
    post_partial_stop_buffer_pct: float = 0.0
    post_partial_trail_reduction: float = 0.6
    
    # === Replay Configuration ===
    replay_tick_interval_seconds: float = 2.0
    
    # === Cooldown ===
    cooldown_duration_seconds: float = 60.0
    loser_suppression_enabled: bool = True
    loser_streak_threshold: int = 3
    extended_cooldown_multiplier: float = 3.0
    
    # === RSI Configuration ===
    rsi_period: int = 14
    rsi_entry_enabled: bool = False
    rsi_oversold: float = 30.0
    rsi_overbought: float = 70.0
    
    # === Logging ===
    log_file: str = "logs/engine.log"
    log_level: str = "INFO"
    log_format: str = "JSON"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary for logging."""
        return {
            "active_strategy": self.active_strategy,
            "arm_velocity_threshold": self.arm_velocity_threshold,
            "arm_persistence_ticks": self.arm_persistence_ticks,
            "arm_timeout_seconds": self.arm_timeout_seconds,
            "velocity_lookback_ticks": self.velocity_lookback_ticks,
            "acceleration_window_ticks": self.acceleration_window_ticks,
            "position_size_usd": self.position_size_usd,
            "atr_stop_multiplier": self.atr_stop_multiplier,
            "atr_period_ticks": self.atr_period_ticks,
            "trailing_stop_pct": self.trailing_stop_pct,
            "signal_decay_enabled": self.signal_decay_enabled,
            "partial_profit_enabled": self.partial_profit_enabled,
            "partial_take_pct": self.partial_take_pct,
            "partial_take_pct_trending": self.partial_take_pct_trending,
            "partial_take_pct_ranging": self.partial_take_pct_ranging,
            "partial_close_ratio": self.partial_close_ratio,
            "post_partial_stop_buffer_pct": self.post_partial_stop_buffer_pct,
            "post_partial_trail_reduction": self.post_partial_trail_reduction,
            "replay_tick_interval_seconds": self.replay_tick_interval_seconds,
            "cooldown_duration_seconds": self.cooldown_duration_seconds,
            "loser_suppression_enabled": self.loser_suppression_enabled,
            "loser_streak_threshold": self.loser_streak_threshold,
            "extended_cooldown_multiplier": self.extended_cooldown_multiplier,
            "rsi_period": self.rsi_period,
            "rsi_entry_enabled": self.rsi_entry_enabled,
            "rsi_oversold": self.rsi_oversold,
            "rsi_overbought": self.rsi_overbought,
        }
    
    def __str__(self) -> str:
        """Human-readable config summary."""
        return (
            f"EngineConfig(v4.0)\n"
            f"  Strategy: {self.active_strategy}\n"
            f"  ARM: vel>{self.arm_velocity_threshold}, persist={self.arm_persistence_ticks}ticks\n"
            f"  Risk: ATR_stop={self.atr_stop_multiplier}x, trail={self.trailing_stop_pct*100}%\n"
            f"  Partial: trending={self.partial_take_pct_trending*100}%, ranging={self.partial_take_pct_ranging*100}%\n"
            f"  Loser: enabled={self.loser_suppression_enabled}\n"
            f")"
        )

# Default configuration instance
DEFAULT_CONFIG = EngineConfig()
