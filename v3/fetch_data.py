"""
Fetch historical data from Binance.

Downloads 1-minute OHLCV candles and saves to CSV.

Usage:
    python fetch_data.py BTCUSDT 2024-01-01 2024-01-03
"""

import sys
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path


def fetch_binance_data(symbol: str, start_date: str, end_date: str, output_file: str):
    """
    Fetch data from Binance and save to CSV.
    
    Args:
        symbol: Trading pair (e.g., "BTCUSDT")
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        output_file: Output CSV path
    """
    try:
        import ccxt
    except ImportError:
        print("Error: ccxt not installed. Install with: pip install ccxt")
        sys.exit(1)
    
    print(f"Fetching {symbol} data from {start_date} to {end_date}...")
    
    # Initialize exchange
    exchange = ccxt.binance({
        'enableRateLimit': True,
    })
    
    # Convert dates to timestamps
    start_ts = exchange.parse8601(f"{start_date}T00:00:00Z")
    end_ts = exchange.parse8601(f"{end_date}T23:59:59Z")
    
    # Fetch data in chunks (Binance limit = 1000 candles per request)
    all_candles = []
    current_ts = start_ts
    
    while current_ts < end_ts:
        print(f"Fetching from {datetime.fromtimestamp(current_ts/1000).strftime('%Y-%m-%d %H:%M')}...")
        
        candles = exchange.fetch_ohlcv(
            symbol=symbol.replace('USDT', '/USDT'),  # Format: BTC/USDT
            timeframe='1m',
            since=current_ts,
            limit=1000
        )
        
        if not candles:
            break
        
        all_candles.extend(candles)
        
        # Move to next chunk
        current_ts = candles[-1][0] + 60000  # +1 minute
        
        if current_ts >= end_ts:
            break
    
    # Convert to DataFrame
    df = pd.DataFrame(all_candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    
    # Filter exact date range
    df = df[
        (df['timestamp'] >= pd.to_datetime(start_date)) &
        (df['timestamp'] <= pd.to_datetime(end_date))
    ]
    
    # Remove duplicates
    df = df.drop_duplicates(subset=['timestamp']).reset_index(drop=True)
    
    # Save to CSV
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_file, index=False)
    
    print(f"✓ Saved {len(df)} candles to {output_file}")
    print(f"  Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")


def main():
    if len(sys.argv) < 4:
        print("Usage: python fetch_data.py SYMBOL START_DATE END_DATE [OUTPUT_FILE]")
        print("Example: python fetch_data.py BTCUSDT 2024-01-01 2024-01-03")
        sys.exit(1)
    
    symbol = sys.argv[1]
    start_date = sys.argv[2]
    end_date = sys.argv[3]
    
    # Default output file
    if len(sys.argv) > 4:
        output_file = sys.argv[4]
    else:
        output_file = f"data/{symbol}_1m.csv"
    
    fetch_binance_data(symbol, start_date, end_date, output_file)


if __name__ == '__main__':
    main()
