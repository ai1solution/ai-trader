"""
Generate synthetic test data for the trading engine.

Creates realistic-looking 1-minute OHLCV candles with:
- Trending periods
- Ranging periods
- Volatile periods

Usage:
    python generate_test_data.py --days 2 --output data/test_data.csv
"""

import argparse
import pandas as pd
import numpy as np
from datetime import datetime, timedelta


def generate_synthetic_candles(start_date: str, num_days: int, 
                               base_price: float = 45000.0) -> pd.DataFrame:
    """
    Generate synthetic 1-minute candles.
    
    Args:
        start_date: Start date (YYYY-MM-DD)
        num_days: Number of days to generate
        base_price: Starting price
        
    Returns:
        DataFrame with OHLCV data
    """
    np.random.seed(42)  # For reproducibility
    
    # Calculate number of candles (1440 candles/day)
    num_candles = num_days * 1440
    
    # Generate timestamps
    start_dt = datetime.strptime(start_date, '%Y-%m-%d')
    timestamps = [start_dt + timedelta(minutes=i) for i in range(num_candles)]
    
    # Generate price series with multiple regimes
    prices = []
    current_price = base_price
    
    for i in range(num_candles):
        # Determine regime based on position in dataset
        position_pct = i / num_candles
        
        if position_pct < 0.3:
            # Trending up (first 30%)
            drift = 0.0002  # 0.02% per minute
            volatility = 0.0005
        elif position_pct < 0.5:
            # Ranging (30-50%)
            drift = 0.0
            volatility = 0.0003
        elif position_pct < 0.7:
            # Trending down (50-70%)
            drift = -0.0001
            volatility = 0.0005
        else:
            # Volatile (70-100%)
            drift = 0.0
            volatility = 0.001
        
        # Generate price change
        change = drift + np.random.normal(0, volatility)
        current_price *= (1 + change)
        prices.append(current_price)
    
    # Generate OHLC from price series
    candles = []
    for i, ts in enumerate(timestamps):
        close = prices[i]
        
        # Open is previous close (or base for first candle)
        open_price = prices[i-1] if i > 0 else base_price
        
        # Generate high/low around open-close range
        high_offset = abs(np.random.normal(0, 0.0003))
        low_offset = abs(np.random.normal(0, 0.0003))
        
        high = max(open_price, close) * (1 + high_offset)
        low = min(open_price, close) * (1 - low_offset)
        
        # Ensure OHLC consistency
        high = max(high, open_price, close)
        low = min(low, open_price, close)
        
        # Generate volume (random but realistic)
        volume = np.random.lognormal(7, 0.5)  # Mean around 1000
        
        candles.append({
            'timestamp': ts,
            'open': round(open_price, 2),
            'high': round(high, 2),
            'low': round(low, 2),
            'close': round(close, 2),
            'volume': round(volume, 2)
        })
    
    df = pd.DataFrame(candles)
    return df


def main():
    parser = argparse.ArgumentParser(description="Generate synthetic test data")
    
    parser.add_argument(
        '--start',
        type=str,
        default='2024-01-01',
        help='Start date (YYYY-MM-DD)'
    )
    
    parser.add_argument(
        '--days',
        type=int,
        default=2,
        help='Number of days to generate'
    )
    
    parser.add_argument(
        '--base-price',
        type=float,
        default=45000.0,
        help='Starting price'
    )
    
    parser.add_argument(
        '--output',
        type=str,
        default='data/test_data.csv',
        help='Output CSV file'
    )
    
    args = parser.parse_args()
    
    print(f"Generating {args.days} days of synthetic data...")
    print(f"Start date: {args.start}")
    print(f"Base price: ${args.base_price:,.2f}")
    
    df = generate_synthetic_candles(args.start, args.days, args.base_price)
    
    # Save to CSV
    from pathlib import Path
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    df.to_csv(args.output, index=False)
    
    print(f"\n✓ Generated {len(df)} candles")
    print(f"  Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
    print(f"  Price range: ${df['close'].min():,.2f} to ${df['close'].max():,.2f}")
    print(f"  Saved to: {args.output}")
    print("\nReady for testing!")
    print(f"  python main.py --mode replay --symbol BTCUSDT --data-file {args.output}")


if __name__ == '__main__':
    main()
