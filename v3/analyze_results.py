"""
Analyze trading results from engine logs.

Parses JSON logs and calculates:
- Total PnL
- Win rate
- Average win/loss
- Maximum drawdown

Usage:
    python analyze_results.py logs/engine.log
"""

import json
import sys
from collections import defaultdict


def analyze_logs(log_file: str):
    """
    Analyze engine logs.
    
    Args:
        log_file: Path to JSON log file
    """
    trades = []
    
    # Parse logs
    with open(log_file, 'r') as f:
        for line in f:
            if not line.strip():
                continue
            try:
                entry = json.loads(line)
                
                # Collect exit events (have PnL)
                if entry.get('event') == 'POSITION_EXIT' and 'pnl' in entry:
                    trades.append({
                        'timestamp': entry['timestamp'],
                        'symbol': entry['symbol'],
                        'pnl': entry['pnl'],
                        'reason': entry.get('reason', 'unknown'),
                        'entry_price': entry.get('entry_price'),
                        'exit_price': entry.get('exit_price'),
                    })
            except json.JSONDecodeError:
                continue
    
    if not trades:
        print("No trades found in log file.")
        return
    
    # Calculate statistics
    total_pnl = sum(t['pnl'] for t in trades)
    wins = [t for t in trades if t['pnl'] > 0]
    losses = [t for t in trades if t['pnl'] <= 0]
    
    win_rate = len(wins) / len(trades) * 100 if trades else 0
    avg_win = sum(t['pnl'] for t in wins) / len(wins) if wins else 0
    avg_loss = sum(t['pnl'] for t in losses) / len(losses) if losses else 0
    
    # Exit reason breakdown
    exit_reasons = defaultdict(int)
    for t in trades:
        exit_reasons[t['reason']] += 1
    
    # Cumulative PnL for drawdown
    cumulative_pnl = []
    running_pnl = 0
    for t in trades:
        running_pnl += t['pnl']
        cumulative_pnl.append(running_pnl)
    
    max_pnl = max(cumulative_pnl) if cumulative_pnl else 0
    max_drawdown = max_pnl - min(cumulative_pnl) if cumulative_pnl else 0
    
    # Print results
    print("\n" + "=" * 70)
    print("TRADING RESULTS ANALYSIS")
    print("=" * 70)
    print(f"\nTotal Trades:        {len(trades)}")
    print(f"Wins:                {len(wins)} ({win_rate:.1f}%)")
    print(f"Losses:              {len(losses)} ({100-win_rate:.1f}%)")
    print(f"\nTotal PnL:           ${total_pnl:.2f}")
    print(f"Average Win:         ${avg_win:.2f}")
    print(f"Average Loss:        ${avg_loss:.2f}")
    print(f"Win/Loss Ratio:      {abs(avg_win/avg_loss):.2f}x" if avg_loss != 0 else "N/A")
    print(f"\nMax Drawdown:        ${max_drawdown:.2f}")
    print(f"\nExit Reasons:")
    for reason, count in sorted(exit_reasons.items(), key=lambda x: -x[1]):
        pct = count / len(trades) * 100
        print(f"  {reason:20s} {count:3d} ({pct:.1f}%)")
    
    print("\n" + "=" * 70)
    print("\nFirst 5 Trades:")
    for i, t in enumerate(trades[:5], 1):
        print(f"  {i}. {t['timestamp'][:19]} | PnL: ${t['pnl']:7.2f} | Reason: {t['reason']}")
    
    print("\nLast 5 Trades:")
    for i, t in enumerate(trades[-5:], len(trades)-4):
        print(f"  {i}. {t['timestamp'][:19]} | PnL: ${t['pnl']:7.2f} | Reason: {t['reason']}")
    
    print("\n" + "=" * 70)


def main():
    if len(sys.argv) < 2:
        print("Usage: python analyze_results.py <log_file>")
        print("Example: python analyze_results.py logs/engine.log")
        sys.exit(1)
    
    log_file = sys.argv[1]
    analyze_logs(log_file)


if __name__ == '__main__':
    main()

# python v3/live_mock.py --symbols AIA/USDT BOT/USDT DOLO/USDT DAM/USDT AIX/USDT CC/USDT