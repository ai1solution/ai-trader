import time
import json
import os
import csv
import math
import logging
from datetime import datetime, timedelta, timezone
from collections import deque, defaultdict
from enum import Enum, auto
import ccxt

# --- Configuration ---
# Example Window (Recent Past relative to System Time 2025-12-28)
# Kraken OHLCV public API only provides recent data (last ~720-1000 intervals).
# We default to the last 24 hours to ensure data is available for the runner.
START_DATE_STR = "2025-12-28 10:00:00"
END_DATE_STR   = "2025-12-28 22:00:00"
CHUNK_SIZE_MINUTES = 60
TIMEFRAME = '1m'
EXCHANGE_ID = 'kraken'

# Output Files
TRADES_CSV = "historical_trades.csv"
SUMMARY_CSV = "historical_summary.csv"

# Replicating V11 Universe
TARGET_ASSETS = [
    'BTC/USD', 'ETH/USD', 'SOL/USD', 'DOGE/USD', 'PEPE/USD', 
    'WIF/USD', 'SHIB/USD', 'BONK/USD', 'NEAR/USD', 'FET/USD'
]

CORRELATION_MAP = {
    'BTC/USD': 'MAJOR', 'ETH/USD': 'MAJOR', 'SOL/USD': 'MAJOR',
    'DOGE/USD': 'MEME', 'PEPE/USD': 'MEME', 'WIF/USD': 'MEME', 
    'SHIB/USD': 'MEME', 'BONK/USD': 'MEME',
    'NEAR/USD': 'ALT', 'FET/USD': 'ALT'
}

# --- Mocking Logging ---
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger("Backtest")

def log_event(message, level="INFO"):
    pass 

# --- COPIED CLASSES FROM V11 Engine (Modified for Simulation) ---

class TradeState(Enum):
    WAIT = auto()
    ARM = auto()
    ENTRY = auto()
    HOLD = auto()
    EXIT = auto()
    COOLDOWN = auto()

class MarketRegime(Enum):
    TRENDING = "TRENDING"
    CHOP = "CHOP"
    LOW_VOL = "LOW_VOL"

class SymbolData:
    def __init__(self, symbol):
        self.symbol = symbol
        self.state = TradeState.WAIT
        self.price_history = deque(maxlen=20)   
        self.velocity_history = deque(maxlen=5) 
        self.last_price = 0.0
        
        # Risk & Governors
        self.consecutive_losses = 0
        self.cooldown_expires = 0 # Timestamp
        self.heat_score = 0                     
        self.last_trade_time = 0
        
        # State Machine Tracking
        self.arm_streak = 0
        self.entry_velocity = 0.0
        self.entry_trend_dir = 0
        
        # V11.1 Entry Metadata
        self.entry_regime = None
        self.entry_quality = "MEDIUM" 
        self.entry_atr_pct = 0.0
        self.entry_spread_pct = 0.0
        self.entry_velocity_slope = 0.0
        self.last_arm_time = 0
        self.last_arm_start_time = 0 

    def update_price(self, price):
        self.last_price = price
        self.price_history.append(price)
        
    def get_velocity(self):
        if len(self.price_history) < 10:
            return 0.0
        old_price = self.price_history[-10]
        if old_price == 0: return 0.0
        return ((self.last_price - old_price) / old_price) * 100

class RegimeDetector:
    @staticmethod
    def detect(tickers_data_map, symbol_map):
        velocities = []
        for sym, data in symbol_map.items():
            if not data.price_history: continue
            vel = abs(data.get_velocity())
            velocities.append(vel)
            
        if not velocities:
            return MarketRegime.CHOP 
            
        median_vel = sorted(velocities)[len(velocities)//2]
        
        if median_vel < 0.05:
            return MarketRegime.LOW_VOL
        elif median_vel > 0.25:
            return MarketRegime.TRENDING
        else:
            return MarketRegime.CHOP

class RiskManager:
    @staticmethod
    def can_enter(symbol, portfolio, regime):
        if regime == MarketRegime.CHOP:
            return False, "Regime CHOP"
            
        if len(portfolio) >= 3:
            return False, "Max Portfolio Heat (3)"
            
        category = CORRELATION_MAP.get(symbol, 'OTHER')
        same_cat_count = sum(1 for t in portfolio if CORRELATION_MAP.get(t['symbol']) == category)
        
        if category == 'MEME' and same_cat_count >= 1:
            return False, "Max MEME Heat (1)"
        if category == 'MAJOR' and same_cat_count >= 2:
            return False, "Max MAJOR Heat (2)"
            
        return True, "OK"

    @staticmethod
    def get_effective_threshold(base_threshold, symbol_data):
        inflation = 1.0 + (0.3 * symbol_data.heat_score)
        return indent_threshold(base_threshold * inflation)

def indent_threshold(val):
    return val

class TechnicalAnalysis:
    @staticmethod
    def calculate_atr(highs, lows, closes, period=14):
        if len(closes) < period + 1: return 0.0
        tr_list = []
        for i in range(1, len(closes)):
            h, l, pc = highs[i], lows[i], closes[i-1]
            tr = max(h - l, abs(h - pc), abs(l - pc))
            tr_list.append(tr)
        if not tr_list: return 0.0
        return sum(tr_list[-period:]) / period

    @staticmethod
    def get_trend_alignment(closes, period=20):
        if len(closes) < period: return 0
        sma = sum(closes[-period:]) / period
        return 1 if closes[-1] > sma else -1

def format_price(price):
    if price < 1.0: return f"{price:.8f}"
    else: return f"{price:.2f}"


# --- Data Loading ---

class DataLoader:
    def __init__(self, start_date_str, end_date_str, exchange_id='kraken'):
        self.start_dt = datetime.strptime(start_date_str, "%Y-%m-%d %H:%M:%S")
        self.end_dt = datetime.strptime(end_date_str, "%Y-%m-%d %H:%M:%S")
        self.exchange = getattr(ccxt, exchange_id)()
        self.data_cache = {} 
        
    def fetch_data(self, symbols):
        print(f"Fetching data from {self.start_dt} to {self.end_dt}...")
        
        since = int(self.start_dt.replace(tzinfo=timezone.utc).timestamp() * 1000)
        end_ts = int(self.end_dt.replace(tzinfo=timezone.utc).timestamp() * 1000)
        
        for symbol in symbols:
            print(f"  Loading {symbol}...")
            self.data_cache[symbol] = []
            current_since = since
            
            # Safety break to prevent infinite loop
            loop_safety = 0
            while current_since < end_ts and loop_safety < 100:
                loop_safety += 1
                try:
                    ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe='1m', since=current_since, limit=1000)
                    if not ohlcv:
                        break
                    
                    self.data_cache[symbol].extend(ohlcv)
                    
                    last_ts = ohlcv[-1][0]
                    if last_ts >= end_ts:
                        break
                        
                    current_since = last_ts + 60000 
                    time.sleep(0.5) 
                    
                except Exception as e:
                    print(f"    Error fetching {symbol}: {e}")
                    time.sleep(2)
            
            self.data_cache[symbol] = [
                x for x in self.data_cache[symbol] 
                if x[0] >= since and x[0] <= end_ts
            ]
            print(f"    Loaded {len(self.data_cache[symbol])} candles.")

    def get_chunk_iterator(self, chunk_minutes=60):
        start_ts = int(self.start_dt.replace(tzinfo=timezone.utc).timestamp() * 1000)
        end_ts = int(self.end_dt.replace(tzinfo=timezone.utc).timestamp() * 1000)
        chunk_ms = chunk_minutes * 60 * 1000
        
        current_ts = start_ts
        while current_ts < end_ts:
            next_ts = min(current_ts + chunk_ms, end_ts)
            
            chunk_data = {}
            for sym, candles in self.data_cache.items():
                chunk_data[sym] = [c for c in candles if current_ts <= c[0] < next_ts]
                
            yield current_ts, next_ts, chunk_data
            current_ts = next_ts


# --- Engine Adapter ---

class EngineAdapter:
    def __init__(self, config):
        self.config = config
        self.symbol_map = {sym: SymbolData(sym) for sym in TARGET_ASSETS}
        self.portfolio = []
        self.completed_trades = []
        self.history_buffer = {sym: deque(maxlen=50) for sym in TARGET_ASSETS}
        self.current_time = 0 
        self.skipped_chop = 0
        self.regime_counts = defaultdict(int) 

    def tick(self, timestamp_ms, market_snapshot):
        self.current_time = timestamp_ms / 1000.0
        now = self.current_time
        
        # 1. Update Prices & History
        tickers_mock = {}
        for sym, candle in market_snapshot.items():
            if not candle: continue
            price = candle[4] # Close
            self.symbol_map[sym].update_price(price)
            tickers_mock[sym] = {'last': price} 
            self.history_buffer[sym].append(candle)

        # 2. Detect Regime
        regime = RegimeDetector.detect(tickers_mock, self.symbol_map)
        self.regime_counts[regime.value] += 1
        
        # 3. Logic Loop
        for symbol in TARGET_ASSETS:
            s_data = self.symbol_map[symbol]
            if symbol not in market_snapshot: continue
            
            candle = market_snapshot[symbol]
            price = candle[4]
            
            # --- Technical Analysis ---
            history = list(self.history_buffer[symbol])
            if len(history) > 15:
                closes = [c[4] for c in history]
                highs = [c[2] for c in history]
                lows = [c[3] for c in history]
                atr = TechnicalAnalysis.calculate_atr(highs, lows, closes, period=self.config['ATR_PERIOD'])
                trend_dir = TechnicalAnalysis.get_trend_alignment(closes)
            else:
                atr = price * 0.01 
                trend_dir = 0
            
            current_vel = s_data.get_velocity()
            s_data.velocity_history.append(current_vel)
            
            spread_valid = True

            # --- STATE MACHINE REPLICATION ---
            
            # 1. COOLDOWN
            if s_data.state == TradeState.COOLDOWN:
                if now >= s_data.cooldown_expires:
                    s_data.state = TradeState.WAIT
                    
            # 2. WAIT -> ARM
            if s_data.state == TradeState.WAIT:
                eff_thresh = RiskManager.get_effective_threshold(self.config['VELOCITY_THRESHOLD'], s_data)

                # Check for CHOP skipping stat
                if regime == MarketRegime.CHOP and abs(current_vel) > eff_thresh:
                   self.skipped_chop += 1

                if abs(current_vel) > eff_thresh and regime != MarketRegime.CHOP:
                    s_data.state = TradeState.ARM
                    s_data.arm_streak = 1
                    s_data.last_arm_time = now
                    s_data.last_arm_start_time = now
                else:
                    if s_data.heat_score > 0 and (now - s_data.last_arm_time > 600):
                        s_data.heat_score = max(0, s_data.heat_score - 1)
                        s_data.last_arm_time = now

            # 3. ARM -> ENTRY / WAIT
            elif s_data.state == TradeState.ARM:
                eff_thresh = RiskManager.get_effective_threshold(self.config['VELOCITY_THRESHOLD'], s_data)
                is_persistent = abs(current_vel) > eff_thresh
                
                has_acceleration = False
                if len(s_data.velocity_history) >= 5:
                    recent_vels = list(s_data.velocity_history)
                    med_current = sorted(recent_vels[-3:])[1]
                    med_prev = sum(recent_vels[-5:-3])/2
                    has_acceleration = abs(med_current) > abs(med_prev)
                else:
                    has_acceleration = True
                
                if is_persistent and spread_valid:
                    if not has_acceleration:
                        s_data.state = TradeState.WAIT
                    else:
                        s_data.arm_streak += 1
                        s_data.last_arm_time = now
                        if s_data.arm_streak >= self.config['ARM_PERSISTENCE']:
                            allowed, reason = RiskManager.can_enter(symbol, self.portfolio, regime)
                            if not allowed:
                                if reason == "Regime CHOP":
                                    self.skipped_chop += 1
                                s_data.state = TradeState.WAIT
                            elif ((current_vel > 0 and trend_dir == 1) or (current_vel < 0 and trend_dir == -1)):
                                s_data.state = TradeState.ENTRY
                            else:
                                s_data.state = TradeState.WAIT
                
                if (now - s_data.last_arm_start_time) > 300: 
                     if s_data.arm_streak > 0:
                        s_data.state = TradeState.COOLDOWN
                        s_data.cooldown_expires = now + 60
                     else:
                        s_data.state = TradeState.WAIT

            # 4. ENTRY -> HOLD
            elif s_data.state == TradeState.ENTRY:
                direction = "LONG" if current_vel > 0 else "SHORT"
                atr_multiplier = 3.0 if price < 1.0 else 2.0
                stop_dist = atr * atr_multiplier
                
                active_trade = {
                    'symbol': symbol, 'status': 'OPEN', 'direction': direction,
                    'entry_price': price, 'leverage': self.config['BASE_LEVERAGE'],
                    'stop_loss': price - stop_dist if direction == "LONG" else price + stop_dist,
                    'entry_time': now, 'max_pnl': 0.0,
                    'entry_velocity': current_vel,
                    'entry_regime': regime.value,
                    'entry_time_str': datetime.fromtimestamp(now).strftime('%Y-%m-%d %H:%M:%S'),
                    'regime_at_entry': regime.value, 
                    'entry_quality': s_data.entry_quality,
                    'entry_time_ist': datetime.fromtimestamp(now, timezone(timedelta(hours=5, minutes=30))).strftime('%Y-%m-%d %H:%M:%S')
                }
                
                eqs = "MEDIUM"
                strong_vel = abs(current_vel) > (RiskManager.get_effective_threshold(self.config['VELOCITY_THRESHOLD'], s_data) * 1.3)
                trend_aligned = (regime == MarketRegime.TRENDING)
                if strong_vel and trend_aligned: eqs = "HIGH"
                elif regime == MarketRegime.CHOP: eqs = "LOW"
                s_data.entry_quality = eqs
                active_trade['eqs'] = eqs

                self.portfolio.append(active_trade)
                s_data.state = TradeState.HOLD
                s_data.entry_velocity = current_vel
                s_data.heat_score += 1
                s_data.last_trade_time = now
                s_data.entry_regime = regime
                s_data.entry_trend_dir = trend_dir

            # 5. HOLD -> EXIT
            elif s_data.state == TradeState.HOLD:
                trade = next((t for t in self.portfolio if t['symbol'] == symbol), None)
                if not trade:
                    s_data.state = TradeState.WAIT
                    continue
                
                entry = trade['entry_price']
                direction = trade['direction']
                lev = trade['leverage']
                
                if direction == "LONG": pnl = ((price - entry)/entry)*100*lev
                else: pnl = ((entry - price)/entry)*100*lev
                
                if pnl > trade['max_pnl']: trade['max_pnl'] = pnl
                
                if trade['max_pnl'] > 0.75:
                    new_sl = entry
                    if direction=="LONG" and new_sl > trade['stop_loss']: trade['stop_loss'] = new_sl
                    elif direction=="SHORT" and new_sl < trade['stop_loss']: trade['stop_loss'] = new_sl
                
                exit_reason = None
                if (direction=="LONG" and price <= trade['stop_loss']) or (direction=="SHORT" and price >= trade['stop_loss']):
                    exit_reason = "STOP_LOSS" if pnl < 0 else "PROFIT_RATCHET"
                elif s_data.entry_trend_dir != 0 and trend_dir != s_data.entry_trend_dir and abs(current_vel) < abs(s_data.entry_velocity):
                    exit_reason = "TREND_INVALIDATION"
                else:
                    base_decay = 0.50
                    if s_data.entry_quality == "HIGH": base_decay = 0.30
                    elif s_data.entry_quality == "LOW": base_decay = 0.70
                    if s_data.entry_regime == MarketRegime.TRENDING: base_decay -= 0.10
                    if pnl > 0.5: base_decay += 0.20
                    base_decay = max(0.1, min(0.9, base_decay))
                    
                    if abs(current_vel) < (abs(s_data.entry_velocity) * base_decay):
                        exit_reason = "SIGNAL_DECAY"
                    elif (s_data.entry_velocity > 0 and current_vel < -0.05) or (s_data.entry_velocity < 0 and current_vel > 0.05):
                        exit_reason = "REVERSAL"
                        
                if exit_reason:
                    s_data.state = TradeState.EXIT
                    if pnl < 0:
                        s_data.consecutive_losses += 1
                        mins = 5 if s_data.consecutive_losses==1 else (15 if s_data.consecutive_losses==2 else 60)
                        s_data.cooldown_expires = now + (mins * 60)
                    else:
                        s_data.consecutive_losses = 0
                    
                    self.portfolio.remove(trade)
                    trade['exit_price'] = price
                    trade['exit_time'] = now
                    trade['exit_time_str'] = datetime.fromtimestamp(now).strftime('%Y-%m-%d %H:%M:%S')
                    trade['exit_time_ist'] = datetime.fromtimestamp(now, timezone(timedelta(hours=5, minutes=30))).strftime('%Y-%m-%d %H:%M:%S')
                    trade['exit_reason'] = exit_reason
                    trade['pnl_pct'] = pnl
                    self.completed_trades.append(trade)
            
            # 6. EXIT -> COOLDOWN/WAIT
            elif s_data.state == TradeState.EXIT:
                if s_data.cooldown_expires > now:
                    s_data.state = TradeState.COOLDOWN
                else:
                    s_data.state = TradeState.WAIT


# --- Backtest Runner ---

class BacktestRunner:
    def __init__(self):
        config_defaults = {
            "BASE_LEVERAGE": 10,
            "VELOCITY_THRESHOLD": 0.15,
            "MAX_SPREAD_PCT": 0.1,
            "ATR_PERIOD": 14,
            "POLL_INTERVAL": 60, 
            "ARM_PERSISTENCE": 3
        }
        self.engine = EngineAdapter(config_defaults)
        self.loader = DataLoader(START_DATE_STR, END_DATE_STR, EXCHANGE_ID)
        
    def run(self):
        print("Starting Backtest...")
        self.loader.fetch_data(TARGET_ASSETS)
        
        # Chunking / Iteration
        iterator = self.loader.get_chunk_iterator(CHUNK_SIZE_MINUTES)
        
        total_ticks = 0
        print("Processing chunks...")
        for start_ts, end_ts, chunk_data in iterator:
            all_timestamps = set()
            for sym, candles in chunk_data.items():
                for c in candles:
                    all_timestamps.add(c[0])
            sorted_timestamps = sorted(list(all_timestamps))
            
            for ts in sorted_timestamps:
                snapshot = {}
                for sym, candles in chunk_data.items():
                    matches = [c for c in candles if c[0] == ts]
                    if matches:
                        snapshot[sym] = matches[0]
                if snapshot:
                    self.engine.tick(ts, snapshot)
                    total_ticks += 1
            print(f"  Processed chunk {datetime.fromtimestamp(start_ts/1000)} - {datetime.fromtimestamp(end_ts/1000)}")
            
        self.save_results(total_ticks)

    def save_results(self, total_ticks):
        print(f"Backtest Complete. Total Ticks: {total_ticks}")
        trades = self.engine.completed_trades
        print(f"Total Trades: {len(trades)}")
        
        if not trades:
            print("No trades generated.")
        
        # 1. Trades CSV
        if trades:
            keys = ['symbol', 'direction', 'entry_time_ist', 'entry_price', 'exit_time_ist', 'exit_price', 'exit_reason', 'pnl_pct', 'regime_at_entry', 'entry_quality']
            try:
                with open(TRADES_CSV, 'w', newline='') as f:
                    writer = csv.DictWriter(f, fieldnames=keys, extrasaction='ignore')
                    writer.writeheader()
                    writer.writerows(trades)
                print(f"Saved {TRADES_CSV}")
            except Exception as e:
                print(f"Error saving CSV: {e}")

        # 2. Metrics & Summary
        wins = [t for t in trades if t['pnl_pct'] > 0]
        losses = [t for t in trades if t['pnl_pct'] <= 0]
        win_rate = len(wins) / len(trades) if trades else 0
        total_pnl = sum(t['pnl_pct'] for t in trades)
        
        # Calculate Max Drawdown (Approximate)
        equity = 100.0
        peak = 100.0
        max_dd = 0.0
        
        sorted_trades = sorted(trades, key=lambda x: x['exit_time'])
        for t in sorted_trades:
            equity += t['pnl_pct']
            if equity > peak: peak = equity
            if peak > 0:
                dd_pct = (peak - equity) / peak * 100
                if dd_pct > max_dd: max_dd = dd_pct
        
        # Regime Stats
        total_regime_ticks = sum(self.engine.regime_counts.values())
        regime_dist = {}
        if total_regime_ticks > 0:
            regime_dist = {k: f"{(v/total_regime_ticks*100):.1f}%" for k,v in self.engine.regime_counts.items()}
            
        print("\n--- Efficiency Metrics ---")
        print(f"Win Rate: {win_rate*100:.1f}%")
        print(f"Net PnL (Leveraged): {total_pnl:.2f}%")
        print(f"Max Drawdown: {max_dd:.2f}%")
        print(f"Trades Skipped (CHOP): {self.engine.skipped_chop}")
        print(f"Regime Dist: {regime_dist}")
        
        # 3. Summary CSV
        summary_headers = ['Date', 'Total_Trades', 'Winning_Trades', 'Losing_Trades', 'Net_PnL', 'Max_Drawdown', 'Regime_Distribution', 'Trades_Skipped_Due_To_CHOP']
        try:
            with open(SUMMARY_CSV, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(summary_headers)
                writer.writerow([
                    datetime.now().strftime("%Y-%m-%d"),
                    len(trades),
                    len(wins),
                    len(losses),
                    f"{total_pnl:.2f}",
                    f"{max_dd:.2f}",
                    str(regime_dist),
                    self.engine.skipped_chop
                ])
            print(f"Saved {SUMMARY_CSV}")
        except Exception as e:
            print(f"Error saving Summary CSV: {e}")

if __name__ == "__main__":
    runner = BacktestRunner()
    runner.run()
