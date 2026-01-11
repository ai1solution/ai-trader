
import csv
import sys
from collections import defaultdict

TRAJECTORY_FILE = 'trajectory_replay_v3.csv'

def analyze():
    print(f"Analyzing {TRAJECTORY_FILE}...")
    
    trades = defaultdict(list)
    
    try:
        with open(TRAJECTORY_FILE, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['State'] in ['ENTRY', 'HOLD', 'EXIT']:
                    trades[row['Ticker']].append(row)
    except FileNotFoundError:
        print("Trajectory file not found.")
        return

    if not trades:
        print("No trades found in trajectory.")
        return

    print(f"Found activity for {len(trades)} tickers.")
    
    for ticker, rows in trades.items():
        print(f"\n--- {ticker} ---")
        max_mfe = -999.0
        partial_taken = False
        exit_reason = "N/A"
        
        # Track Entry
        entry_price = 0.0
        
        for row in rows:
            if row['State'] == 'ENTRY':
                 entry_price = float(row['Last_Price'])
            
            # Check MFE
            # MFE in CSV is string, maybe float or '-'
            mfe_str = row.get('MFE', '-')
            if mfe_str != '-':
                try:
                    mfe = float(mfe_str.replace('%', ''))
                    if mfe > max_mfe: max_mfe = mfe
                except: pass
            
            # Check Partial
            if row.get('Partial') == 'TRUE':
                partial_taken = True
                print(f"  [PARTIAL TAKE] at {row['Timestamp']} | PnL: {row['Partial_PnL']}")
                
            if row['State'] == 'EXIT':
                exit_reason = row.get('Exit_Reason', 'Unknown')

        print(f"  Max MFE Recorded: {max_mfe}%")
        print(f"  Partial Taken: {partial_taken}")
        print(f"  Exit Reason: {exit_reason}")

if __name__ == "__main__":
    analyze()
