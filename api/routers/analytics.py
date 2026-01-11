from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from pydantic import BaseModel
import csv
import os
from datetime import datetime
from collections import defaultdict

router = APIRouter(prefix="/analytics", tags=["Analytics"])

class TradeRecord(BaseModel):
    timestamp: str
    symbol: str
    strategy: str
    direction: str
    entry_price: float
    exit_price: float
    quantity: float
    pnl: float
    reason: str

class ProfitAnalysis(BaseModel):
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_pnl: float
    avg_win: float
    avg_loss: float
    largest_win: float
    largest_loss: float
    profit_factor: float
    sharpe_ratio: float
    max_drawdown: float
    by_symbol: dict
    by_strategy: dict

@router.get("/trades/history", response_model=List[TradeRecord])
async def get_trade_history(limit: int = Query(100, description="Number of trades to return")):
    """Get historical trades from CSV"""
    trades_file = "results/trades.csv"
    
    if not os.path.exists(trades_file):
        return []
    
    trades = []
    try:
        with open(trades_file, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                trades.append(TradeRecord(
                    timestamp=row.get('timestamp', ''),
                    symbol=row.get('symbol', ''),
                    strategy=row.get('strategy', ''),
                    direction=row.get('direction', ''),
                    entry_price=float(row.get('entry_price', 0)),
                    exit_price=float(row.get('exit_price', 0)),
                    quantity=float(row.get('quantity', 0)),
                    pnl=float(row.get('pnl', 0)),
                    reason=row.get('reason', '')
                ))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read trades: {str(e)}")
    
    return trades[-limit:]  # Return most recent

@router.get("/profit/analyze", response_model=ProfitAnalysis)
async def analyze_profit():
    """Analyze historical trading performance"""
    trades_file = "results/trades.csv"
    
    if not os.path.exists(trades_file):
        # Return demo data for visualization
        return ProfitAnalysis(
            total_trades=0,
            winning_trades=0,
            losing_trades=0,
            win_rate=0,
            total_pnl=0,
            avg_win=0,
            avg_loss=0,
            largest_win=0,
            largest_loss=0,
            profit_factor=0,
            sharpe_ratio=0,
            max_drawdown=0,
            by_symbol={},
            by_strategy={}
        )
    
    trades = []
    wins = []
    losses = []
    by_symbol = defaultdict(lambda: {'trades': 0, 'pnl': 0})
    by_strategy = defaultdict(lambda: {'trades': 0, 'pnl': 0})
    
    try:
        with open(trades_file, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                pnl = float(row.get('pnl', 0))
                symbol = row.get('symbol', 'UNKNOWN')
                strategy = row.get('strategy', 'UNKNOWN')
                
                trades.append(pnl)
                if pnl > 0:
                    wins.append(pnl)
                elif pnl < 0:
                    losses.append(pnl)
                
                by_symbol[symbol]['trades'] += 1
                by_symbol[symbol]['pnl'] += pnl
                
                by_strategy[strategy]['trades'] += 1
                by_strategy[strategy]['pnl'] += pnl
        
        total_trades = len(trades)
        winning_trades = len(wins)
        losing_trades = len(losses)
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        
        total_pnl = sum(trades)
        avg_win = sum(wins) / len(wins) if wins else 0
        avg_loss = sum(losses) / len(losses) if losses else 0
        largest_win = max(wins) if wins else 0
        largest_loss = min(losses) if losses else 0
        
        total_wins = sum(wins)
        total_losses = abs(sum(losses))
        profit_factor = (total_wins / total_losses) if total_losses > 0 else 0
        
        # Calculate Sharpe (simplified)
        import statistics
        sharpe_ratio = (statistics.mean(trades) / statistics.stdev(trades) * (252 ** 0.5)) if len(trades) > 1 else 0
        
        # Calculate max drawdown
        cumulative = 0
        peak = 0
        max_dd = 0
        for pnl in trades:
            cumulative += pnl
            if cumulative > peak:
                peak = cumulative
            dd = peak - cumulative
            if dd > max_dd:
                max_dd = dd
        
        return ProfitAnalysis(
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=round(win_rate, 2),
            total_pnl=round(total_pnl, 2),
            avg_win=round(avg_win, 2),
            avg_loss=round(avg_loss, 2),
            largest_win=round(largest_win, 2),
            largest_loss=round(largest_loss, 2),
            profit_factor=round(profit_factor, 2),
            sharpe_ratio=round(sharpe_ratio, 2),
            max_drawdown=round(max_dd, 2),
            by_symbol=dict(by_symbol),
            by_strategy=dict(by_strategy)
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

@router.get("/demo/generate")
async def generate_demo_data():
    """Generate demo trading data for visualization"""
    import random
    from datetime import timedelta
    
    demo_trades = []
    symbols = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT']
    strategies = ['momentum', 'mean_reversion']
    
    base_time = datetime.now() - timedelta(days=7)
    cumulative_pnl = 0
    
    for i in range(50):
        symbol = random.choice(symbols)
        strategy = random.choice(strategies)
        direction = random.choice(['LONG', 'SHORT'])
        
        entry = random.uniform(20000, 50000) if symbol == 'BTC/USDT' else random.uniform(1500, 3500)
        exit_price = entry * (1 + random.uniform(-0.03, 0.05))
        quantity = random.uniform(0.01, 0.1)
        
        if direction == 'LONG':
            pnl = (exit_price - entry) * quantity
        else:
            pnl = (entry - exit_price) * quantity
        
        cumulative_pnl += pnl
        
        demo_trades.append({
            'timestamp': (base_time + timedelta(hours=i*2)).isoformat(),
            'symbol': symbol,
            'strategy': strategy,
            'direction': direction,
            'entry_price': round(entry, 2),
            'exit_price': round(exit_price, 2),
            'quantity': round(quantity, 4),
            'pnl': round(pnl, 2),
            'cumulative_pnl': round(cumulative_pnl, 2),
            'reason': random.choice(['TP_HIT', 'SL_HIT', 'SIGNAL_REVERSE'])
        })
    
    return {"trades": demo_trades, "total_pnl": round(cumulative_pnl, 2)}
