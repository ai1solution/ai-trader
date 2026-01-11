import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from v4.strategies.indicators import calculate_ema
import pandas as pd

def test_ema():
    prices = [10, 11, 12, 11, 10, 11, 12, 13, 14, 15]
    ema_5 = calculate_ema(prices, 5)
    print(f"EMA(5): {ema_5}")
    
    # Validation with pandas
    ts = pd.Series(prices)
    pd_ema = ts.ewm(span=5, adjust=False).mean().iloc[-1]
    print(f"Pandas EMA(5): {pd_ema}")

if __name__ == "__main__":
    try:
        test_ema()
    except Exception as e:
        print(e)
