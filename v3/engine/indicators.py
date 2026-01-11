"""
Indicator calculations for the trading engine.

All functions are pure (no side effects) and operate on lists/arrays.
This makes them easy to test and reason about.

Key principle: Velocity is TICK-BASED, not candle-based.
"""

from typing import List, Optional
import statistics
from enum import Enum

from .enums import Regime


def calculate_velocity(prices: List[float], lookback: int) -> Optional[float]:
    """
    Calculate velocity (momentum) over a lookback window.
    
    Velocity = (current_price - price_at_lookback) / price_at_lookback
    
    This is tick-based: lookback refers to N ticks ago, not N candles.
    
    Args:
        prices: List of prices, most recent last
        lookback: Number of ticks to look back
        
    Returns:
        Velocity as a percentage change, or None if insufficient data
        
    Examples:
        prices = [100, 101, 102, 103, 104]
        calculate_velocity(prices, lookback=4) = (104 - 100) / 100 = 0.04 (4%)
    """
    if len(prices) < lookback + 1:
        return None
        
    current_price = prices[-1]
    past_price = prices[-(lookback + 1)]
    
    if past_price == 0:
        return None
        
    velocity = (current_price - past_price) / past_price
    return velocity


def calculate_atr(highs: List[float], lows: List[float], closes: List[float], 
                  period: int) -> Optional[float]:
    """
    Calculate Average True Range (ATR) for volatility measurement.
    
    ATR measures market volatility using true range:
    TR = max(high - low, |high - prev_close|, |low - prev_close|)
    ATR = average of TR over period
    
    Used for stop-loss sizing: wider stops in volatile markets.
    
    Args:
        highs: List of high prices, most recent last
        lows: List of low prices, most recent last
        closes: List of close prices, most recent last
        period: Number of periods for ATR calculation
        
    Returns:
        ATR value, or None if insufficient data
    """
    if len(highs) < period + 1 or len(lows) < period + 1 or len(closes) < period + 1:
        return None
        
    true_ranges = []
    
    for i in range(-period, 0):
        high = highs[i]
        low = lows[i]
        prev_close = closes[i - 1]
        
        # True Range = max of three values
        tr = max(
            high - low,
            abs(high - prev_close),
            abs(low - prev_close)
        )
        true_ranges.append(tr)
    
    # ATR is simple average of true ranges
    atr = statistics.mean(true_ranges)
    return atr


def calculate_velocity_acceleration(velocities: List[float], window: int = 3) -> bool:
    """
    Check if velocity is accelerating.
    
    Acceleration = median(last_N_velocities) > median(prev_N_velocities)
    
    This ensures momentum is INCREASING, not just high.
    Prevents ARM → ENTRY when velocity is high but decelerating.
    
    Why median? More robust to outliers than mean.
    
    Args:
        velocities: List of velocity values, most recent last
        window: Window size for median comparison (default 3)
        
    Returns:
        True if accelerating (recent > previous), False otherwise
        
    Examples:
        velocities = [0.01, 0.02, 0.03, 0.04, 0.05, 0.06]
        window = 3
        last_3 = [0.04, 0.05, 0.06], median = 0.05
        prev_3 = [0.01, 0.02, 0.03], median = 0.02
        Result: True (0.05 > 0.02)
    """
    if len(velocities) < window * 2:
        return False
        
    # Last N velocities
    last_window = velocities[-window:]
    
    # Previous N velocities (before last window)
    prev_window = velocities[-(window * 2):-window]
    
    median_last = statistics.median(last_window)
    median_prev = statistics.median(prev_window)
    
    return median_last > median_prev


def detect_regime(prices: List[float], atr: Optional[float], 
                  lookback: int = 20) -> Regime:
    """
    Detect market regime: TRENDING, RANGING, or VOLATILE.
    
    Used for logging/context only in v3. No entry gating.
    
    Logic:
    - VOLATILE: ATR is high relative to price (>2%)
    - TRENDING: Price has clear directional bias (high abs(slope))
    - RANGING: Otherwise
    
    This is a simple classifier. More sophisticated regime detection
    can be added later without affecting entry/exit logic.
    
    Args:
        prices: List of prices, most recent last
        atr: Current ATR value (can be None)
        lookback: Window for regime calculation
        
    Returns:
        Regime enum: TRENDING, RANGING, or VOLATILE
    """
    if len(prices) < lookback:
        return Regime.RANGING  # Default when insufficient data
        
    recent_prices = prices[-lookback:]
    current_price = prices[-1]
    
    # Check volatility first
    if atr is not None and current_price > 0:
        atr_pct = atr / current_price
        if atr_pct > 0.02:  # ATR > 2% of price
            return Regime.VOLATILE
    
    # Check for trending behavior
    # Simple linear regression slope approximation
    # Positive slope = uptrend, negative = downtrend, flat = ranging
    
    n = len(recent_prices)
    x_mean = (n - 1) / 2  # Mean of indices 0, 1, 2, ..., n-1
    y_mean = statistics.mean(recent_prices)
    
    numerator = sum((i - x_mean) * (recent_prices[i] - y_mean) for i in range(n))
    denominator = sum((i - x_mean) ** 2 for i in range(n))
    
    if denominator == 0:
        return Regime.RANGING
        
    slope = numerator / denominator
    slope_pct = slope / y_mean if y_mean != 0 else 0
    
    # If abs(slope) is significant, we're trending
    if abs(slope_pct) > 0.001:  # 0.1% per tick is trending
        return Regime.TRENDING
    else:
        return Regime.RANGING


def get_signal_type(velocity: Optional[float], threshold: float = 0.0) -> 'SignalType':
    """
    Convert velocity to signal type.
    
    Args:
        velocity: Current velocity value
        threshold: Threshold for NEUTRAL zone (default 0)
        
    Returns:
        SignalType: LONG, SHORT, or NEUTRAL
    """
    # Import here to avoid circular dependency
    from .enums import SignalType
    
    if velocity is None:
        return SignalType.NEUTRAL
        
    if velocity > threshold:
        return SignalType.LONG
    elif velocity < -threshold:
        return SignalType.SHORT
    else:
        return SignalType.NEUTRAL


def calculate_rsi(prices: List[float], period: int = 14) -> Optional[float]:
    """
    Calculate Relative Strength Index (RSI).
    
    RSI = 100 - (100 / (1 + RS))
    RS = Average Gain / Average Loss
    
    Args:
        prices: List of prices
        period: RSI period (default 14)
        
    Returns:
        RSI value (0-100), or None if insufficient data
    """
    if len(prices) < period + 1:
        return None
        
    gains = []
    losses = []
    
    # Calculate initial changes
    # Use last N+1 prices to get N changes
    window = prices[-(period + 1):]
    
    for i in range(1, len(window)):
        change = window[i] - window[i-1]
        if change > 0:
            gains.append(change)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(abs(change))
            
    avg_gain = statistics.mean(gains)
    avg_loss = statistics.mean(losses)
    
    if avg_loss == 0:
        return 100.0
        
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi
