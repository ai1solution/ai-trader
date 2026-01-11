"""
Research Top Coins

Analyzes recent market data (last 3 days) to identify coins with:
1. Highest Daily Returns
2. Highest Volatility (ATR)
3. Best Trading Opportunities for our Engine

Usage:
    python research_top_coins.py
"""

import pandas as pd
from datetime import datetime, timedelta
import ccxt
from rich.console import Console
from rich.table import Table
import numpy as np

console = Console()

# Candidate Pool (High Volume/Cap)
CANDIDATES = [
    # Majors
    "BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT", "ADA/USDT",
    # Volatile L1/L2
    "AVAX/USDT", "MATIC/USDT", "DOT/USDT", "LINK/USDT", "NEAR/USDT",
    "JUP/USDT", "TIA/USDT", "SEI/USDT", "SUI/USDT", "APT/USDT",
    "OP/USDT", "ARB/USDT", "INJ/USDT", "RUNE/USDT", "FTM/USDT",
    # Meme/Speculative (High Volatility)
    "DOGE/USDT", "SHIB/USDT", "PEPE/USDT", "FLOKI/USDT", "BONK/USDT",
    "WIF/USDT", "ORDI/USDT", "SATS/USDT", "MEME/USDT", 
    # Legacy/DeFi
    "LDO/USDT", "UNI/USDT", "AAVE/USDT", "MKR/USDT", "SNX/USDT",
    "FIL/USDT", "LTC/USDT", "BCH/USDT", "ETC/USDT", "EOS/USDT"
]

def fetch_recent_metrics(symbol: str, days: int = 3):
    try:
        # Determine timeframe
        # Using 1h candles to check volatility
        since = int((datetime.now() - timedelta(days=days)).timestamp() * 1000)
        
        exchange = ccxt.binance()
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe='1h', since=since, limit=72)
        
        if not ohlcv:
            return None
            
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        
        # Metrics
        # 1. Total Return over period
        start_price = df['open'].iloc[0]
        end_price = df['close'].iloc[-1]
        raw_return = (end_price - start_price) / start_price * 100
        
        # 2. Max Daily Move (High - Low)
        # Resample to daily if needed, or just look at hourly volatility
        df['range_pct'] = (df['high'] - df['low']) / df['open'] * 100
        avg_volatility = df['range_pct'].mean()
        max_volatility = df['range_pct'].max()
        
        return {
            "symbol": symbol.replace("/", ""),
            "price": end_price,
            "return_3d": raw_return,
            "avg_vol_1h": avg_volatility,
            "max_vol_1h": max_volatility,
            "score": abs(raw_return) + (avg_volatility * 10) # Weighted score
        }
    except Exception as e:
        # console.print(f"Error fetching {symbol}: {e}")
        return None

def main():
    console.print(f"[blue]Researching {len(CANDIDATES)} coins for top performers (Last 3 Days)...[/blue]")
    
    results = []
    
    import concurrent.futures
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(fetch_recent_metrics, coin) for coin in CANDIDATES]
        
        from rich.progress import track
        for future in track(concurrent.futures.as_completed(futures), total=len(CANDIDATES), description="Analyzing..."):
            res = future.result()
            if res:
                results.append(res)
    
    # Sort by Score (Volatility + Return)
    results.sort(key=lambda x: x['score'], reverse=True)
    
    # Selection: Top 15
    top_coins = results[:15]
    
    table = Table(title="Top 15 Volatile Opportunities")
    table.add_column("Rank")
    table.add_column("Symbol", style="cyan")
    table.add_column("Price (8dp)")
    table.add_column("3D Return", justify="right")
    table.add_column("Avg 1H Vol", justify="right")
    table.add_column("Score", justify="right")
    
    formatted_list = []
    
    for i, r in enumerate(top_coins):
        # 8 Decimal Precision as requested
        price_str = f"{r['price']:.8f}"
        
        # Return color
        ret = r['return_3d']
        color = "green" if ret > 0 else "red"
        
        table.add_row(
            str(i+1),
            r['symbol'],
            price_str,
            f"[{color}]{ret:+.2f}%[/{color}]",
            f"{r['avg_vol_1h']:.2f}%",
            f"{r['score']:.1f}"
        )
        formatted_list.append(r['symbol'])
        
    console.print(table)
    
    console.print("\n[bold yellow]Recommended Coin List for Live Runner:[/bold yellow]")
    print(formatted_list)

if __name__ == "__main__":
    main()
