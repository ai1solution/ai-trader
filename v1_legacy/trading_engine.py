import time
import sys
import json
import os
import logging
import math
import random
import csv
from datetime import datetime
from collections import deque, defaultdict
from enum import Enum, auto
import ccxt
from rich.console import Console
from rich.table import Table
from rich.live import Live
from rich.panel import Panel
from rich.text import Text
from rich.progress import Progress, BarColumn, TextColumn
from rich import print as rprint
from rich.layout import Layout
from rich.console import Group

# Import Market Feed Abstraction
try:
    from market_data_feed import LiveFeed, HistoricalFeed, MarketDataFeed
except ImportError:
    # Fallback or local dev
    pass

# --- Configuration & Constants ---
CONFIG_FILE = "config.json"
LOG_FILE = "engine.log"
TRAJECTORY_FILE = "trajectory.csv"
STATE_FILE = "active_trades.json"

# V11 "Action-First Command Center" Universe
TARGET_ASSETS = [
    'BTC/USD', 'ETH/USD', 'SOL/USD', 'DOGE/USD', 'PEPE/USD', 
    'WIF/USD', 'SHIB/USD', 'BONK/USD', 'NEAR/USD', 'FET/USD'
]

# Defines active correlation groups (Majors vs Memes vs Alts)
CORRELATION_MAP = {
    'BTC/USD': 'MAJOR', 'ETH/USD': 'MAJOR', 'SOL/USD': 'MAJOR',
    'DOGE/USD': 'MEME', 'PEPE/USD': 'MEME', 'WIF/USD': 'MEME', 
    'SHIB/USD': 'MEME', 'BONK/USD': 'MEME',
    'NEAR/USD': 'ALT', 'FET/USD': 'ALT'
}

console = Console()

# --- Logging Setup ---
def setup_logging():
    logging.basicConfig(
        filename=LOG_FILE,
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

setup_logging()

setup_logging()

# Global override for Replay timestamp
REPLAY_CURRENT_TIME = None 

def log_event(message, level="INFO"):
    global REPLAY_CURRENT_TIME
    
    prefix = ""
    if REPLAY_CURRENT_TIME:
        # Override timestamp in message or prefix
        prefix = f"[REPLAY] timestamp={datetime.fromtimestamp(REPLAY_CURRENT_TIME).strftime('%Y-%m-%d %H:%M:%S')} | "
    
    full_msg = f"{prefix}{message}"
    
    if level == "INFO": logging.info(full_msg)
    elif level == "WARNING": logging.warning(full_msg)
    elif level == "ERROR": logging.error(full_msg)

# --- Class Definitions ---

class TradeState(Enum):
    WAIT = auto()       # Default, scanning
    ARM = auto()        # Velocity threshold crossed, waiting for persistence
    ENTRY = auto()      # Signal confirmed, trade executed
    HOLD = auto()       # Active trade management
    EXIT = auto()       # Trade closing
    COOLDOWN = auto()   # Suppressed after loss

class MarketRegime(Enum):
    TRENDING = "TRENDING"
    CHOP = "CHOP"
    LOW_VOL = "LOW_VOL"

class SymbolData:
    def __init__(self, symbol):
        self.symbol = symbol
        self.state = TradeState.WAIT
        self.price_history = deque(maxlen=20)   # For raw velocity calc
        self.velocity_history = deque(maxlen=6) # For signal persistence and acceleration (need 6 for prev 3 vs last 3)
        self.last_price = 0.0
        
        # Risk & Governors
        self.consecutive_losses = 0
        self.cooldown_expires = 0
        self.heat_score = 0                     # Number of entries in recent window
        self.last_trade_time = 0
        
        # State Machine Tracking
        self.arm_streak = 0                     # Count of consecutive scans in ARM criteria
        self.entry_velocity = 0.0
        self.entry_trend_dir = 0
        
        # V11.1 Entry Metadata
        self.entry_regime = None
        self.entry_quality = "MEDIUM" # V11.2 EQS
        self.entry_atr_pct = 0.0
        self.entry_spread_pct = 0.0
        self.entry_velocity_slope = 0.0
        self.last_arm_time = 0
        self.last_arm_start_time = 0 # V11.2 For ARM Timeout

        
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
    def detect(tickers_data, symbol_map):
        """
        Detects global market regime based on Median ATR and Velocity Dispersion.
        """
        velocities = []
        atrs = []
        
        for sym, data in symbol_map.items():
            if not data.price_history: continue
            vel = abs(data.get_velocity())
            velocities.append(vel)
            # Rough ATR proxy if real ATR not available per tick in this simplistic view
            # In real loop we have calculated ATR. We will pass it in if possible, 
            # for now we rely on velocity dispersion as primary proxy for regime.
            
        if not velocities:
            return MarketRegime.CHOP # Default safe
            
        median_vel = sorted(velocities)[len(velocities)//2]
        
        # Heuristics for Crypto Regimes (10-tick velocity %):
        # < 0.05% -> Low Vol
        # > 0.30% -> Trending
        # Mixed/High Dispersion -> Chop?
        
        # Simple Logic V11:
        if median_vel < 0.05:
            return MarketRegime.LOW_VOL
        # V11.2 Early Trend Detection
        # If median velocity is decent (0.15-0.25) but not yet "Trending" (0.25+)
        # We can implement a check in the main loop or here. 
        # For strictness, we'll keep the regime buckets simple but add logic in the engine.
        elif median_vel > 0.25:
            return MarketRegime.TRENDING
        else:
            return MarketRegime.CHOP

class RiskManager:
    @staticmethod
    def can_enter(symbol, portfolio, regime):
        # 1. Regime Check
        if regime == MarketRegime.CHOP:
            return False, "Regime CHOP"
            
        # 2. Portfolio Heat (Total active trades)
        if len(portfolio) >= 3:
            return False, "Max Portfolio Heat (3)"
            
        # 3. Correlation Check
        category = CORRELATION_MAP.get(symbol, 'OTHER')
        same_cat_count = sum(1 for t in portfolio if CORRELATION_MAP.get(t['symbol']) == category)
        
        if category == 'MEME' and same_cat_count >= 1:
            return False, "Max MEME Heat (1)"
        if category == 'MAJOR' and same_cat_count >= 2:
            return False, "Max MAJOR Heat (2)"
            
        return True, "OK"

    @staticmethod
    def get_effective_threshold(base_threshold, symbol_data):
        # Inflate threshold based on recent activity to prevent over-trading
        inflation = 1.0 + (0.3 * symbol_data.heat_score)
        return indent_threshold(base_threshold * inflation)

def indent_threshold(val):
    return val

# --- Persistence Layer ---
class Persistence:
    @staticmethod
    def save_portfolio(portfolio):
        try:
            with open(STATE_FILE, 'w') as f:
                json.dump(portfolio, f, indent=4)
        except Exception as e:
            log_event(f"Save State Failed: {e}", "ERROR")

    @staticmethod
    def load_portfolio():
        try:
            if os.path.exists(STATE_FILE):
                with open(STATE_FILE, 'r') as f:
                    return json.load(f)
        except Exception as e:
            log_event(f"Load State Failed: {e}", "ERROR")
        return []

# --- Trajectory Logging ---
class TrajectoryLogger:
    @staticmethod
    def init():
        if not os.path.exists(TRAJECTORY_FILE):
            with open(TRAJECTORY_FILE, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'Timestamp', 'Ticker', 'State', 'Regime', 'Velocity', 
                    'Entry_Vel', 'Decay_Pct', 'Heat', 'EQS', 'Action', 'Advisor_Msg',
                    'Last_Price', 'MFE', 'Exit_Reason', 'Replay_Mode',
                    'Partial','Partial_PnL','Rem_Size'
                ])

    @staticmethod
    def log(ticker, state, regime, vel, entry_vel, decay, heat, eqs, action, msg, last_price, mfe, exit_reason, partial, partial_pnl, rem_size):
        try:
            with open(TRAJECTORY_FILE, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    datetime.fromtimestamp(REPLAY_CURRENT_TIME).strftime('%Y-%m-%d %H:%M:%S') if REPLAY_CURRENT_TIME else datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    ticker,
                    state,
                    regime,
                    f"{vel:.4f}",
                    f"{entry_vel:.4f}" if entry_vel else "0",
                    f"{decay:.2f}%" if decay else "0%",
                    heat,
                    eqs,
                    action,
                    msg,
                    f"{last_price}",
                    mfe,
                    exit_reason,
                    "TRUE" if REPLAY_CURRENT_TIME else "FALSE",
                    partial,
                    f"{partial_pnl:.2f}%",
                    f"{rem_size:.2f}"
                ])
        except Exception as e:
            pass

# --- Configuration Load/Save ---
def load_config():
    defaults = {
        "BASE_LEVERAGE": 10,
        "VELOCITY_THRESHOLD": 0.15,
        "MAX_SPREAD_PCT": 0.1,
        "ATR_PERIOD": 14,
        "POLL_INTERVAL": 2,
        "ARM_PERSISTENCE": 3, # Scans required to persist
        "ARM_TIMEOUT_SECONDS": 30, # Duration before ARM resets to WAIT
        "PARTIAL_TAKE_PCT": 0.6, # Trigger for partial profit
        "PARTIAL_CLOSE_RATIO": 0.5 # Percentage of position to close
    }
    if not os.path.exists(CONFIG_FILE):
        return defaults
    with open(CONFIG_FILE, 'r') as f:
        try:
            config = json.load(f)
            for k, v in defaults.items():
                if k not in config: config[k] = v
            return config
        except:
            return defaults

# --- Helper Functions ---
def format_price(price):
    return f"{price:.8f}".rstrip('0').rstrip('.')

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

# --- MAIN ENGINE ---
def run_command_center(market_feed: MarketDataFeed = None):
    # Global ref for logging
    global REPLAY_CURRENT_TIME
    
    console.clear()
    TrajectoryLogger.init()
    
    # 1. Dependency Injection / Default fallback
    if market_feed is None:
        console.print("[yellow]No feed provided, starting LIVE mode via CCXT...[/yellow]")
        market_feed = LiveFeed()
        REPLAY_CURRENT_TIME = None
    else:
        if isinstance(market_feed, HistoricalFeed):
            console.print("[bold cyan]STARTING ENGINE IN REPLAY MODE[/bold cyan]")
            REPLAY_CURRENT_TIME = market_feed.now() # Init
        else:
             REPLAY_CURRENT_TIME = None

    config = load_config()
    portfolio = Persistence.load_portfolio()
    
    # Initialize Symbol State
    symbol_map = {sym: SymbolData(sym) for sym in TARGET_ASSETS}
    
    # Sync Portfolio with SymbolMap (Restore HOLD states)
    for trade in portfolio:
        sym = trade['symbol']
        if sym in symbol_map:
            symbol_map[sym].state = TradeState.HOLD
            # Restore critical trade data
            if 'entry_velocity' in trade:
                symbol_map[sym].entry_velocity = trade['entry_velocity']
            if 'eqs' in trade:
                symbol_map[sym].entry_quality = trade['eqs']
            if 'entry_regime' in trade:
                 symbol_map[sym].entry_regime = MarketRegime(trade['entry_regime']) if trade['entry_regime'] in ["TRENDING", "CHOP", "LOW_VOL"] else None
    
    analysis_cache = {}
    
    progress = Progress(
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        TextColumn("{task.fields[timer]}"),
        expand=True
    )
    task_id = progress.add_task("Next Scan", total=config['POLL_INTERVAL'], timer="2.0s")
    
    layout = Layout()
    layout.split_column(Layout(name="action_panel", size=5), Layout(name="market_data"))
    
    session_start_time = market_feed.now()
    MAX_SESSION_DURATION = 7200

    with Live(layout, console=console, screen=True, refresh_per_second=4) as live:
        while not market_feed.is_finished():
            try:
                # 0. Timeout
                current_time = market_feed.now()
                REPLAY_CURRENT_TIME = current_time if isinstance(market_feed, HistoricalFeed) else None
                
                if current_time - session_start_time > MAX_SESSION_DURATION:
                    console.print("[bold red]⏱️ Session Limit Reached[/]")
                    break

                # 1. Fetch
                start_ts = market_feed.now()
                try:
                    tickers = market_feed.get_tickers(TARGET_ASSETS)
                except:
                    tickers = {}
                fetch_dur = market_feed.now() - start_ts
                
                if not tickers:
                    market_feed.sleep(1)
                    continue

                # 2. Global Regime Detection
                # Update prices first
                for sym, data in tickers.items():
                    if 'last' in data and sym in symbol_map:
                        symbol_map[sym].update_price(float(data['last']))
                
                regime = RegimeDetector.detect(tickers, symbol_map)
                
                # 3. Tables & Logic
                master_table = Table(
                    title=f"V11.0 'COMMAND CENTER' | Regime: {regime.value} | Active: {len(portfolio)} | Latency: {fetch_dur*1000:.0f}ms", 
                    style="bold white", expand=True, padding=(0, 1)
                )
                master_table.add_column("Ticker", style="cyan", width=12)
                master_table.add_column("State", justify="center", width=10)
                master_table.add_column("Entry Details", justify="right", width=18)
                master_table.add_column("Current Price", justify="right", width=12)
                master_table.add_column("PnL ($100)", justify="right", width=12)
                master_table.add_column("Stop", justify="right", width=10)
                master_table.add_column("Velocity", justify="right", width=10)
                master_table.add_column("Signal", justify="center", width=14)
                master_table.add_column("Advisor", justify="left")

                user_actions = []
                trades_to_save = False
                user_actions = []
                trades_to_save = False
                now = market_feed.now()

                for symbol in TARGET_ASSETS:
                    s_data = symbol_map[symbol] # SymbolData
                    exit_reason = None
                    ticker_data = tickers.get(symbol)
                    if not ticker_data or not s_data.last_price: continue

                    price = s_data.last_price
                    
                    # Caching Technicals
                    if symbol not in analysis_cache or (now - analysis_cache[symbol]['ts'] > 300):
                        try:
                            # Use market_feed.fetch_ohlcv
                            ohlcv = market_feed.fetch_ohlcv(symbol, timeframe='1m', limit=50)
                            if not ohlcv: raise Exception("No Data")
                            
                            closes = [x[4] for x in ohlcv]
                            atr = TechnicalAnalysis.calculate_atr([x[2] for x in ohlcv], [x[3] for x in ohlcv], closes, config['ATR_PERIOD'])
                            trend_dir = TechnicalAnalysis.get_trend_alignment(closes)
                            analysis_cache[symbol] = {'atr': atr, 'trend': trend_dir, 'ts': now}
                        except:
                            analysis_cache[symbol] = {'atr': price*0.01, 'trend': 0, 'ts': now} 
                    
                    cached = analysis_cache[symbol]
                    atr = cached['atr']
                    trend_dir = cached['trend']
                    
                    spread_valid = True
                    bid = ticker_data.get('bid', price)
                    ask = ticker_data.get('ask', price)
                    spread_pct = ((ask - bid) / ask) * 100 if ask > 0 else 0
                    if spread_pct > config['MAX_SPREAD_PCT']: spread_valid = False

                    current_vel = s_data.get_velocity()
                    s_data.velocity_history.append(current_vel)

                    # --- STATE MACHINE TRANSITIONS ---
                    
                    # 1. COOLDOWN CHECK
                    if s_data.state == TradeState.COOLDOWN:
                        if now >= s_data.cooldown_expires:
                            s_data.state = TradeState.WAIT
                            log_event(f"{symbol} Cooldown Expired. Resuming WAIT.")
                    
                    # 2. WAIT -> ARM
                    if s_data.state == TradeState.WAIT:
                        # Effective Threshold (Dynamic)
                        eff_thresh = RiskManager.get_effective_threshold(config['VELOCITY_THRESHOLD'], s_data)

                        if abs(current_vel) > eff_thresh and regime != MarketRegime.CHOP:
                            s_data.state = TradeState.ARM
                            s_data.arm_streak = 1
                            s_data.last_arm_time = now
                            s_data.last_arm_start_time = now # V11.2 Start Timer
                            log_event(f"{symbol} -> ARMED (Vel: {current_vel:.2f}%)")
                        else:
                            # Heat Decay Logic (V11.1 Improved)
                            # Decay heat if no ARM for 10 minutes (600s)
                            if s_data.heat_score > 0 and (now - s_data.last_arm_time > 600):
                                s_data.heat_score = max(0, s_data.heat_score - 1)
                                s_data.last_arm_time = now # Reset to prevent rapid decay, decay once per interval check


                    # 3. ARM -> ENTRY / WAIT
                    elif s_data.state == TradeState.ARM:
                        eff_thresh = RiskManager.get_effective_threshold(config['VELOCITY_THRESHOLD'], s_data)
                        
                        # Check Persistence
                        is_persistent = abs(current_vel) > eff_thresh
                        
                        # V11.2 Acceleration Filter
                        # Requirement: Velocity MUST be increasing (convexity) to enter.
                        # prevents catching the tail end of a spike.
                        has_acceleration = False
                        
                        if len(s_data.velocity_history) >= 6:
                            recent_vels = list(s_data.velocity_history)
                            # Median of Last 3 (Current window)
                            med_current = sorted(recent_vels[-3:])[1]
                            # Median of Previous 3 (Previous window)
                            med_prev = sorted(recent_vels[-6:-3])[1]
                            
                            # Check: Is current momentum significantly higher than previous?
                            has_acceleration = abs(med_current) > abs(med_prev)
                        elif len(s_data.velocity_history) >= 2:
                             # Warmup fallback: Simple slope
                             has_acceleration = abs(current_vel) > abs(s_data.velocity_history[-2])
                        else:
                            has_acceleration = True # Startup

                        # V11.2 ARM Timeout Logic
                        # Ensure we use 'now' (Market/Replay Time) not wall clock
                        time_in_arm = now - s_data.last_arm_start_time
                        is_timed_out = time_in_arm > config['ARM_TIMEOUT_SECONDS']
                        
                        if is_persistent and spread_valid:
                            if is_timed_out:
                                s_data.state = TradeState.WAIT
                                s_data.cooldown_expires = now + 30 # Micro cooldown (configurable?)
                                s_data.state = TradeState.COOLDOWN
                                log_event(f"{symbol} ARM RESET: TIMEOUT ({time_in_arm:.1f}s > {config['ARM_TIMEOUT_SECONDS']}s)")
                            elif not has_acceleration:
                                s_data.state = TradeState.WAIT
                                log_event(f"{symbol} ARM RESET: NO_ACCELERATION (Vel Slope Flat/Negative)")
                            else:
                                s_data.arm_streak += 1
                                s_data.last_arm_time = now
                                if s_data.arm_streak >= config['ARM_PERSISTENCE']:
                                    # Try ENTRY
                                    allowed, reason = RiskManager.can_enter(symbol, portfolio, regime)
                                    if allowed and ((current_vel > 0 and trend_dir == 1) or (current_vel < 0 and trend_dir == -1)):
                                        s_data.state = TradeState.ENTRY
                                    else:
                                        s_data.state = TradeState.WAIT # Failed Risk or Trend
                                        log_event(f"{symbol} ARM Failed: {reason} or Trend Mismatch")
                        else:
                            # Not persistent (vel dropped below threshold)
                            s_data.state = TradeState.WAIT
                            log_event(f"{symbol} ARM RESET: MOMENTUM_LOST")

                            
                    # 4. ENTRY -> HOLD
                    elif s_data.state == TradeState.ENTRY:
                        # Execute Trade Logic immediately
                        direction = "LONG" if current_vel > 0 else "SHORT"
                        atr_multiplier = 3.0 if price < 1.0 else 2.0
                        stop_dist = atr * atr_multiplier
                        
                        active_trade = {
                            'symbol': symbol, 'status': 'OPEN', 'direction': direction,
                            'entry_price': price, 'leverage': config['BASE_LEVERAGE'],
                            'stop_loss': price - stop_dist if direction == "LONG" else price + stop_dist,
                            'entry_time': now, 'max_pnl': 0.0,
                            'entry_velocity': current_vel,
                            'entry_regime': regime.value,
                            'partial_taken': False,
                            'partial_pnl': 0.0,
                            'remaining_size': 1.0
                        }
                        portfolio.append(active_trade)
                        trades_to_save = True
                        
                        # Reset consecutive losses on entry? No, only on win/loss close.
                        # But we can update last_active time
                        # s_data.entry_quality computed below
                        
                        # Update Symbol Data & Record Entry Metadata
                        s_data.state = TradeState.HOLD
                        s_data.entry_velocity = current_vel
                        s_data.heat_score += 1
                        s_data.last_trade_time = now
                        
                        # V11.1 Store Entry Metadata
                        s_data.entry_regime = regime
                        s_data.entry_atr_pct = (atr / price) * 100
                        s_data.entry_spread_pct = spread_pct
                        s_data.entry_velocity_slope = 0.0 # Placeholder, would need more complex history analysis
                        s_data.entry_trend_dir = trend_dir

                        
                        formatted_ticker = f"[{symbol.split('/')[0]}]"
                        user_actions.append(f"🔵 OPEN {direction} {formatted_ticker} @ {format_price(price)}")
                        # V11.2 ENTRY QUALITY SCORE (EQS)
                        # Default MEDIUM
                        eqs = "MEDIUM"
                        
                        # Criteria
                        strong_vel = abs(current_vel) > (RiskManager.get_effective_threshold(config['VELOCITY_THRESHOLD'], s_data) * 1.3)
                        tight_spread = spread_pct < 0.06
                        trend_aligned = (regime == MarketRegime.TRENDING)
                        
                        if strong_vel and has_acceleration and tight_spread and trend_aligned:
                            eqs = "HIGH"
                        elif (not tight_spread) or (regime == MarketRegime.CHOP):
                            eqs = "LOW"
                        
                        s_data.entry_quality = eqs
                        
                        active_trade['eqs'] = eqs # Store in trade for easy access? Or just keep in symbol data.
                        # Actually hold logic uses s_data.entry_quality, so we are good.
                        
                        formatted_ticker = f"[{symbol.split('/')[0]}]"
                        user_actions.append(f"🔵 OPEN {direction} ({eqs}) {formatted_ticker} @ {format_price(price)}")
                        log_event(f"ENTRY {symbol} {direction} ({eqs}) @ {format_price(price)}")

                    # 5. HOLD -> EXIT Logic (Signal Decay & Management)
                    elif s_data.state == TradeState.HOLD:
                        # Find the trade object
                        trade = next((t for t in portfolio if t['symbol'] == symbol), None)
                        if not trade:
                            s_data.state = TradeState.WAIT # Should not happen
                            continue
                            
                        # A. Calculate PnL
                        try:
                            entry = trade['entry_price']
                            stop_loss = trade['stop_loss']
                            direction = trade['direction']
                            lev = trade['leverage']
                            rem_size = trade.get('remaining_size', 1.0)
                        except KeyError as e:
                            log_event(f"Corrupt trade state for {symbol}: missing {e}. Removing trade.", "ERROR")
                            portfolio.remove(trade)
                            s_data.state = TradeState.WAIT
                            continue
                        
                        # Current PnL (on remaining size)
                        if direction == "LONG": raw_pnl = ((price - entry)/entry)*100*lev
                        else: raw_pnl = ((entry - price)/entry)*100*lev
                        
                        # Max PnL Tracking
                        if raw_pnl > trade['max_pnl']: trade['max_pnl'] = raw_pnl

                        # --- PARTIAL PROFIT TAKING (V11.3) ---
                        # Trigger: Max PnL >= Threshold AND Not Taken AND Current PnL > 0 (Sanity)
                        if not trade.get('partial_taken', False):
                            if trade['max_pnl'] >= config['PARTIAL_TAKE_PCT'] and raw_pnl > 0.1: # Ensure actual profit
                                # EXECUTE PARTIAL
                                trade['partial_taken'] = True
                                trade['remaining_size'] = 1.0 - config['PARTIAL_CLOSE_RATIO']
                                trade['partial_pnl'] = raw_pnl # Lock this PnL for the closed portion
                                rem_size = trade['remaining_size']
                                
                                # Monotonic Stop Tightening
                                # Secure the bag: Move stop to at least Breakeven + small buffer
                                buffer = entry * 0.001 # 0.1% buffer
                                if direction == "LONG":
                                    new_stop = entry + buffer
                                    trade['stop_loss'] = max(trade['stop_loss'], new_stop)
                                else:
                                    new_stop = entry - buffer
                                    trade['stop_loss'] = min(trade['stop_loss'], new_stop)
                                
                                trades_to_save = True
                                log_event(f"PARTIAL TAKE {symbol} | Locked {config['PARTIAL_CLOSE_RATIO']*100}% @ {raw_pnl:.2f}% PnL")
                                user_actions.append(f"💰 PARTIAL TAKE {symbol} (+{raw_pnl:.2f}%)")

                        # Weighted Total PnL (for Display/Logic)
                        # realized_part + unrealized_part
                        # Logic: (partial_pnl * closed_ratio) + (current_pnl * remaining_ratio)
                        if trade.get('partial_taken', False):
                            closed_ratio = 1.0 - rem_size
                            weighted_pnl = (trade['partial_pnl'] * closed_ratio) + (raw_pnl * rem_size)
                        else:
                            weighted_pnl = raw_pnl

                        # B. Ratchet Logic
                        # Use Weighted PnL or Max PnL? 
                        # Standard Ratchets should respect the remaining position's health.
                        # We use trade['max_pnl'] (which is based on price excursion) for ratchet triggers,
                        # but ensure we don't loosen stops.
                        
                        if trade['max_pnl'] > 0.75: # Breakeven+
                            new_sl = entry
                            if direction=="LONG" and new_sl > stop_loss: trade['stop_loss'] = new_sl; trades_to_save=True
                            elif direction=="SHORT" and new_sl < stop_loss: trade['stop_loss'] = new_sl; trades_to_save=True
                            elif direction=="SHORT" and new_sl < sub_stop: trade['stop_loss'] = new_sl; trades_to_save=True
                        if trade['max_pnl'] > 3.0: # Lock Profit
                            new_sl = entry * 1.015 if direction=="LONG" else entry * 0.985
                            if direction=="LONG" and new_sl > trade['stop_loss']: trade['stop_loss'] = new_sl; trades_to_save=True
                            elif direction=="SHORT" and new_sl < trade['stop_loss']: trade['stop_loss'] = new_sl; trades_to_save=True

                        # V11.2 Micro Profit-Take
                        # If PnL > 0.8% and Velocity Weakens (< 80% of entry), Lock 0.5%
                        if trade['max_pnl'] > 0.8:
                            curr_vel_ratio = abs(current_vel) / abs(s_data.entry_velocity) if s_data.entry_velocity else 0
                            if curr_vel_ratio < 0.8:
                                # Tighten Stop to Entry + 0.5%
                                lock_price = entry * 1.005 if direction == "LONG" else entry * 0.995
                                # Check if this is better than current stop
                                if direction == "LONG" and lock_price > trade['stop_loss']:
                                    trade['stop_loss'] = lock_price
                                    trades_to_save = True
                                    log_event(f"{symbol} Micro-Profit Lock Triggered")
                                elif direction == "SHORT" and lock_price < trade['stop_loss']:
                                    trade['stop_loss'] = lock_price
                                    trades_to_save = True
                                    log_event(f"{symbol} Micro-Profit Lock Triggered")

                        # C. Exit Triggers
                        exit_reason = None
                        
                        # 1. Stop Loss / Ratchet Hit
                        if (direction=="LONG" and price <= trade['stop_loss']) or (direction=="SHORT" and price >= trade['stop_loss']):
                            exit_reason = "STOP_LOSS" if raw_pnl < 0 else "PROFIT_RATCHET"
                        
                        # 2. V11.1: Regime-Aware Signal Decay & Trend Validation
                        
                        # A. Trend Re-validation
                        # If trend flipped against us AND velocity is weakening (< entry velocity)
                        elif s_data.entry_trend_dir != 0 and trend_dir != s_data.entry_trend_dir and abs(current_vel) < abs(s_data.entry_velocity):
                            exit_reason = "TREND_INVALIDATION"

                        # B. Regime-Aware Signal Decay
                        else:
                            # Dynamic Decay Thresholds
                            # TRENDING: 40% retention needed (Exit if < 40% of entry) -> tightest on momentum loss? 
                            # Wait, "Exit if < X% of entry" means:
                            # TRENDING: Exit if < 40% (Holds longer?) NO. 
                            # User Requirement: "TRENDING 35–40% of entry velocity", "CHOP 60% of entry velocity"
                            
                            # Dynamic Decay Thresholds based on Entry Quality
                            # HIGH EQS: Patient (30%)
                            # MED EQS: Normal (50%)
                            # LOW EQS: Impatient (70%)
                            
                            base_decay = 0.50
                            if s_data.entry_quality == "HIGH": base_decay = 0.30
                            elif s_data.entry_quality == "LOW": base_decay = 0.70
                            
                            # Regime Modifiers
                            if s_data.entry_regime == MarketRegime.TRENDING:
                                base_decay -= 0.10 # Allow more breathing room in trends
                            
                            # Profit Protection Modifier (V11.2)
                            # If PnL > 0.5%, we tighten up. We don't want to give it back.
                            # Increase required velocity retention (raise decay threshold)
                            if weighted_pnl > 0.5:
                                base_decay += 0.20 
                                
                            # Clamp
                            base_decay = max(0.1, min(0.9, base_decay))
                            
                            if abs(current_vel) < (abs(s_data.entry_velocity) * base_decay):
                                exit_reason = "SIGNAL_DECAY"
                            elif (s_data.entry_velocity > 0 and current_vel < -0.05) or (s_data.entry_velocity < 0 and current_vel > 0.05):
                                exit_reason = "REVERSAL"

                        
                        # Exec Exit?
                        if exit_reason:
                            s_data.state = TradeState.EXIT
                            # Handle PnL outcome for Cooldown
                            if weighted_pnl < 0:
                                s_data.consecutive_losses += 1
                                # Escalate: 1st=5m, 2nd=15m, 3rd=60m
                                mins = 5 if s_data.consecutive_losses==1 else (15 if s_data.consecutive_losses==2 else 60)
                                s_data.cooldown_expires = now + (mins * 60)
                            else:
                                s_data.consecutive_losses = 0 # Reset on win
                            
                            portfolio.remove(trade)
                            trades_to_save = True
                            user_actions.append(f"🔴 CLOSE {symbol} ({exit_reason}) PnL: {weighted_pnl:.2f}%")
                            log_event(f"EXIT {symbol} {exit_reason} PnL: {weighted_pnl:.2f}")

                    # 6. EXIT -> COOLDOWN or WAIT
                    elif s_data.state == TradeState.EXIT:
                        if s_data.cooldown_expires > now:
                            s_data.state = TradeState.COOLDOWN
                        else:
                            s_data.state = TradeState.WAIT

                    # --- ROW FORMATTING ---
                    
                    state_color = {
                        TradeState.WAIT: "white", TradeState.ARM: "yellow", TradeState.ENTRY: "bold green",
                        TradeState.HOLD: "green", TradeState.EXIT: "red", TradeState.COOLDOWN: "blue"
                    }.get(s_data.state, "white")
                    state_display = f"[{state_color}]{s_data.state.name}[/{state_color}]"
                    
                    if s_data.state == TradeState.ARM:
                        state_display += f" ({s_data.arm_streak}/{config['ARM_PERSISTENCE']})"
                    
                    # Log Price Snapshot (V11.1 Requirement)
                    log_event(f"PRICE SNAPSHOT | symbol={symbol} | last={price} | bid={bid} | ask={ask} | spread={spread_pct:.3f}%")
                    
                    entry_display = "-"
                    stop_display = "-"
                    pnl_display = "-"
                    active_t = next((t for t in portfolio if t['symbol'] == symbol), None)

                    if active_t:
                        # Display Weighted PnL
                        entry = active_t['entry_price']
                        lev = active_t['leverage']
                        rem_size = active_t.get('remaining_size', 1.0)
                        
                        entry_time_ts = active_t['entry_time']
                        try:
                            # Handle both float timestamp and datetime if applicable
                            ts = entry_time_ts if isinstance(entry_time_ts, float) else time.mktime(entry_time_ts.timetuple())
                            entry_time_str = datetime.fromtimestamp(ts).strftime('%H:%M:%S')
                        except:
                            entry_time_str = "?"

                        entry_display = f"{format_price(entry)}\n[dim]{entry_time_str}[/dim]"
                        stop_display = format_price(active_t['stop_loss'])
                        
                        if active_t['direction'] == "LONG": curr_raw = ((price - entry)/entry)*100*lev
                        else: curr_raw = ((entry - price)/entry)*100*lev
                        
                        if active_t.get('partial_taken', False):
                             w_pnl = (active_t['partial_pnl'] * (1-rem_size)) + (curr_raw * rem_size)
                        else:
                             w_pnl = curr_raw

                        color = "green" if w_pnl > 0 else "red"
                        # Dollar PnL based on $100 investment = Percentage PnL
                        dollar_val = w_pnl
                        pnl_display = f"[{color}]${dollar_val:.2f}[/{color}]"
                        if active_t.get('partial_taken', False):
                            pnl_display += " [bold yellow]½[/]"
                    
                    vel_color = "green" if current_vel > 0 else "red"
                    
                    # Advisor Logic
                    adv_msg = {
                        TradeState.WAIT: "Scanning...",
                        TradeState.ARM: "⚠️ Signal Building...",
                        TradeState.ENTRY: "🚀 EXECUTE",
                        TradeState.HOLD: "🛡️ Managing Trade",
                        TradeState.EXIT: "Closing...",
                        TradeState.COOLDOWN: f"❄️ Cooling ({(s_data.cooldown_expires - now)/60:.0f}m)"
                    }.get(s_data.state, "")

                    master_table.add_row(
                        symbol, state_display,
                        entry_display,
                        format_price(price), 
                        pnl_display,
                        stop_display,
                        f"[{vel_color}]{current_vel:.2f}%[/{vel_color}]",
                        "ACTIVE" if active_t else "-",
                        adv_msg
                    )
                    
                    # Log Trajectory
                    decay_pct = 0.0
                    if s_data.entry_velocity != 0:
                        decay_pct = (1 - (abs(current_vel) / abs(s_data.entry_velocity))) * 100
                        
                    TrajectoryLogger.log(
                        symbol, s_data.state.name, regime.value, current_vel,
                        s_data.entry_velocity, decay_pct, s_data.heat_score,
                        s_data.entry_quality if s_data.state in [TradeState.HOLD, TradeState.EXIT] else "-",
                        "ACTION" if s_data.state in [TradeState.ENTRY, TradeState.EXIT] else "WAIT",
                        adv_msg, price, 
                        f"{trade['max_pnl']:.2f}%" if active_t else "-", # MFE
                        exit_reason if exit_reason else "-",
                        "TRUE" if active_t and active_t.get('partial_taken', False) else "FALSE",
                        active_t.get('partial_pnl', 0.0) if active_t else 0.0,
                        active_t.get('remaining_size', 0.0) if active_t else 0.0
                    )

                if trades_to_save:
                    Persistence.save_portfolio(portfolio)

                # Update UI
                if user_actions:
                    txt = "\n".join(set(user_actions))
                    panel = Panel(Text(txt, style="bold white on red", justify="center"), 
                                  title="[bold yellow]⚡ BATTLE STATIONS ⚡[/]", style="on red")
                else:
                    panel = Panel(Text("🟢 MARKET MONITOR ACTIVE", style="bold green", justify="center"), 
                                  title="STATUS: SCANNING", style="green")
                
                layout["action_panel"].update(panel)
                layout["market_data"].update(Group(master_table, progress))
                live.update(layout)

                # Progress Loop
                # We need to respect the simulated sleep.
                # If replay speed is max, we don't really want to render progress bar steps 10 times?
                # But to preserve logic, we will call market_feed.sleep 10 times.
                
                step_dur = config['POLL_INTERVAL']/10
                for i in range(10):
                    market_feed.sleep(step_dur)
                    progress.update(task_id, completed=(i+1)*10)

            except KeyboardInterrupt:
                console.print("[red]STOPPED[/]")
                break
            except Exception as e:
                log_event(f"Loop Error: {e}", "ERROR")
                market_feed.sleep(5)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="V1 Trading Engine")
    parser.add_argument("--symbols", nargs="+", help="List of symbols to trade (e.g. BTC/USD ETH/USD)")
    args = parser.parse_args()
    
    if args.symbols:
        TARGET_ASSETS = args.symbols
        console.print(f"[yellow]Overriding symbols with CLI args: {TARGET_ASSETS}[/yellow]")

    run_command_center()
