import ccxt
import pandas as pd
import numpy as np
from datetime import datetime
import sys
import os

def fetch_data(symbol, start_date, end_date):
    print(f"Fetching {symbol} ({start_date} to {end_date})...")
    exchange = ccxt.binance({'enableRateLimit': True})
    since = exchange.parse8601(f"{start_date}T00:00:00Z")
    end_ts = exchange.parse8601(f"{end_date}T23:59:59Z")
    
    all_candles = []
    while since < end_ts:
        candles = exchange.fetch_ohlcv(symbol.replace('USDT', '/USDT'), '1h', since, 1000)
        if not candles: break
        all_candles.extend(candles)
        since = candles[-1][0] + 3600000 # 1h
        
    df = pd.DataFrame(all_candles, columns=['ts', 'open', 'high', 'low', 'close', 'vol'])
    df['dt'] = pd.to_datetime(df['ts'], unit='ms')
    return df

def analyze_df(df, name):
    df['returns'] = df['close'].pct_change()
    df['volatility'] = df['returns'].rolling(24).std()
    
    # Trend: Simple moving average slope (24h)
    df['sma_24'] = df['close'].rolling(24).mean()
    df['trend_strength'] = (df['close'] - df['sma_24']) / df['sma_24']
    
    avg_vol = df['volatility'].mean() * 100
    max_vol = df['volatility'].max() * 100
    
    # Count trend days (where trend strength > 2%)
    trend_hours = (df['trend_strength'].abs() > 0.02).sum()
    total_hours = len(df)
    trend_pct = (trend_hours / total_hours) * 100 if total_hours > 0 else 0
    
    print(f"\n--- {name} ---")
    print(f"Avg Hourly Volatility: {avg_vol:.2f}%")
    print(f"Max Hourly Volatility: {max_vol:.2f}%")
    print(f"Trending Hours (>2% dev): {trend_pct:.1f}%")
    
    # Price change
    start_price = df.iloc[0]['close']
    end_price = df.iloc[-1]['close']
    change = ((end_price - start_price) / start_price) * 100
    print(f"Net Price Change: {change:+.2f}%")

def main():
    coins = ['SUIUSDT', 'SNXUSDT', 'PEPEUSDT']
    periods = [
        ('Dec 2025', '2025-12-01', '2025-12-31'),
        ('Jan 2026', '2026-01-01', '2026-01-08')
    ]
    
    try:
        for coin in coins:
            print(f"\nAnalyzing {coin}...")
            for p_name, start, end in periods:
                df = fetch_data(coin, start, end)
                if not df.empty:
                    analyze_df(df, f"{coin} - {p_name}")
                else:
                    print(f"No data for {p_name}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
