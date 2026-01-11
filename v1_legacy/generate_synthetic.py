import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def generate_synthetic_data():
    symbols = ['BTC/USD', 'ETH/USD', 'SOL/USD', 'DOGE/USD', 'PEPE/USD', 'WIF/USD', 'SHIB/USD', 'BONK/USD', 'NEAR/USD', 'FET/USD']
    base_prices = {'BTC/USD': 90000, 'ETH/USD': 3000, 'SOL/USD': 150, 'DOGE/USD': 0.15, 'PEPE/USD': 0.00001, 
                   'WIF/USD': 2.0, 'SHIB/USD': 0.00002, 'BONK/USD': 0.00002, 'NEAR/USD': 5.0, 'FET/USD': 1.5}
    
    start_time = datetime(2025, 12, 26, 8, 0, 0)
    data = []
    
    # Generate 120 minutes of data at 2-second intervals
    # 120 mins * 30 intervals/min = 3600 steps
    steps = 3600
    for i in range(steps): 
        timestamp = start_time + timedelta(seconds=i*2)
        ts_str = timestamp.strftime('%Y-%m-%d %H:%M:%S')
        
        # Scenario: 
        # 0-30m (0-900): Flat/Low Vol
        # 30-35m (900-1050): Pump
        # 35-40m (1050-1200): Continue Pump
        # 40-60m (1200+): Flat/Chop
        
        for sym in symbols:
            base = base_prices[sym]
            
            if i < 900:
                price = base * (1 + np.random.normal(0, 0.00001)) # Flat
            elif 900 <= i < 1200:
                # Exponential Pump to maintain constant/growing velocity
                # We want velocity ~ 0.2% per 10 steps (20s)
                # (P_new - P_old)/P_old = 0.002
                # Growth factor per step (2s) roughly 1.0002
                steps_in = i - 900
                growth_factor = 1.0003 # Aggressive pump
                price = base * (growth_factor ** steps_in)
            else:
                price = base * (1.0003 ** 300) * (1 + np.random.normal(0, 0.00001)) # Plateau high
                
            vol = 1000
            
            # Trajectory CSV Format:
            # Symbol,Timestamp_IST,Open,High,Low,Close,Volume
            row = {
                'Symbol': sym,
                'Timestamp_IST': ts_str,
                'Open': price,
                'High': price,
                'Low': price,
                'Close': price,
                'Volume': vol
            }
            data.append(row)
            
    df = pd.DataFrame(data)
    df.to_csv('historical_trajectory_synthetic_pump.csv', index=False)
    print("Created historical_trajectory_synthetic_pump.csv")

if __name__ == "__main__":
    generate_synthetic_data()
