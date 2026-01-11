import ccxt
import csv
import time
import logging
from datetime import datetime, timedelta, timezone
from collections import deque
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

# --- CONFIGURATION (USER EDITABLE) ---
START_TIME_IST = "2025-12-28 08:00:00"  # Format: YYYY-MM-DD HH:MM:SS
END_TIME_IST   = "2025-12-28 12:00:00"
TIMEZONE_OFFSET = timedelta(hours=5, minutes=30) # IST is UTC+5:30

TARGET_ASSETS = [
    'BTC/USD', 'ETH/USD', 'SOL/USD', 'DOGE/USD', 'PEPE/USD', 
    'WIF/USD', 'SHIB/USD', 'BONK/USD', 'NEAR/USD', 'FET/USD'
]

OUTPUT_FILE = f"historical_trajectory_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

# --- SYSTEM CONSTANTS (MATCHING ENGINE) ---
VELOCITY_PERIOD = 10     # minutes (candles) for velocity
ATR_PERIOD = 14          # candles for ATR
TREND_SMA_PERIOD = 20    # candles for Trend Alignment
VELOCITY_THRESHOLD = 0.15 # % change
ARM_PERSISTENCE = 3      # Candles to persist

# --- SETUP ---
console = Console()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def ist_to_utc_timestamp(ist_str):
    """Converts IST string to UTC timestamp (ms)."""
    dt = datetime.strptime(ist_str, "%Y-%m-%d %H:%M:%S")
    # Treat naive string as IST
    dt = dt.replace(tzinfo=timezone(TIMEZONE_OFFSET)) 
    return int(dt.timestamp() * 1000)

def timestamp_to_ist_str(ts_ms):
    """Converts UTC timestamp (ms) to IST string."""
    dt = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc)
    ist_dt = dt.astimezone(timezone(TIMEZONE_OFFSET))
    return ist_dt.strftime("%Y-%m-%d %H:%M:%S")

class MarketRegime:
    TRENDING = "TRENDING"
    CHOP = "CHOP"
    LOW_VOL = "LOW_VOL"

class ReplaySymbolData:
    def __init__(self, symbol):
        self.symbol = symbol
        self.closes = deque()
        self.highs = deque()
        self.lows = deque()
        # State
        self.state = "WAIT"
        self.arm_streak = 0
        self.entry_price = 0.0
        self.entry_velocity = 0.0
        self.entry_trend = 0
        self.entry_quality = "-" # Logic placeholder

    def update(self, open_, high, low, close):
        self.closes.append(close)
        self.highs.append(high)
        self.lows.append(low)
        # Keep enough history for indicators
        max_len = max(VELOCITY_PERIOD, ATR_PERIOD, TREND_SMA_PERIOD) + 5
        if len(self.closes) > max_len:
            self.closes.popleft()
            self.highs.popleft()
            self.lows.popleft()

    def get_velocity(self):
        if len(self.closes) < 1: return 0.0
        # Instant velocity: % change from previous candle? 
        # Engine uses price_history deque maxlen 20, "old_price = -10".
        # Engine logic: ((last - old) / old) * 100 where old is 10 ticks ago.
        # Here we use 10 candles ago to approximate.
        if len(self.closes) <= VELOCITY_PERIOD:
            old_price = self.closes[0]
        else:
            old_price = self.closes[-(VELOCITY_PERIOD + 1)]
            
        if old_price == 0: return 0.0
        current = self.closes[-1]
        return ((current - old_price) / old_price) * 100

    def get_atr(self):
        if len(self.closes) < ATR_PERIOD + 1: return 0.0
        # Simple ATR calculation
        tr_list = []
        # Calculate last N TRs
        # Need history corresponding to ATR_PERIOD
        # Iterate backwards
        count = 0
        for i in range(1, ATR_PERIOD + 1):
            if len(self.closes) - i - 1 < 0: break
            
            curr_h = self.highs[-(i)]
            curr_l = self.lows[-(i)]
            prev_c = self.closes[-(i+1)]
            
            # TR = max(high-low, abs(high-prev_close), abs(low-prev_close))
            val1 = curr_h - curr_l
            val2 = abs(curr_h - prev_c)
            val3 = abs(curr_l - prev_c)
            tr = max(val1, val2, val3)
            
            tr_list.append(tr)
            
        if not tr_list: return 0.0
        return sum(tr_list) / len(tr_list)

    def get_trend(self):
        if len(self.closes) < TREND_SMA_PERIOD: return 0
        sma = sum(list(self.closes)[-TREND_SMA_PERIOD:]) / TREND_SMA_PERIOD
        return 1 if self.closes[-1] > sma else -1

def fetch_historical_data(exchange, symbols, start_ms, end_ms):
    """Fetches 1m OHLCV data for all symbols."""
    data_map = {} # {symbol: {timestamp_ms: {o,h,l,c,v}}}
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
    ) as progress:
        task = progress.add_task("Fetching Data...", total=len(symbols))
        
        for symbol in symbols:
            progress.update(task, description=f"Fetching {symbol}")
            symbol_data = {}
            current_start = start_ms
            
            while current_start < end_ms:
                try:
                    ohlcv = exchange.fetch_ohlcv(symbol, '1m', since=current_start, limit=1440) # Max 1440 candles
                    if not ohlcv:
                        break
                    
                    last_ts = 0
                    for candle in ohlcv:
                        ts, o, h, l, c, v = candle
                        if ts > end_ms: break
                        symbol_data[ts] = {'o': o, 'h': h, 'l': l, 'c': c, 'v': v}
                        last_ts = ts
                    
                    current_start = last_ts + 60000 # Next minute
                    time.sleep(exchange.rateLimit / 1000 * 1.5) # Respect rate limits
                    
                    if len(ohlcv) < 1440:
                        break # End of available data
                        
                except Exception as e:
                    console.print(f"[red]Error fetching {symbol}: {e}[/red]")
                    time.sleep(5)
                    continue
            
            data_map[symbol] = symbol_data
            progress.advance(task)
            
    return data_map


def run_replay():
    console.print(f"[bold cyan]Starting Historical Scraper[/bold cyan]")
    console.print(f"Time Window (IST): {START_TIME_IST} -> {END_TIME_IST}")
    
    start_ms = ist_to_utc_timestamp(START_TIME_IST)
    end_ms = ist_to_utc_timestamp(END_TIME_IST)
    
    exchange = ccxt.kraken()
    
    # 1. Fetch Data
    console.print("[yellow]Connecting to Kraken...[/yellow]")
    data_map = fetch_historical_data(exchange, TARGET_ASSETS, start_ms, end_ms)
    
    # Verify data integrity
    timestamps = set()
    for sym in data_map:
        timestamps.update(data_map[sym].keys())
    
    if not timestamps:
        console.print("[red]No data found for the specified range![/red]")
        return

    sorted_timestamps = sorted(list(timestamps))
    console.print(f"[green]Loaded {len(sorted_timestamps)} time steps across {len(TARGET_ASSETS)} assets.[/green]")
    
    # 2. Replay Loop
    csv_file = open(OUTPUT_FILE, 'w', newline='')
    csv_writer = csv.writer(csv_file)
    csv_writer.writerow([
        'Timestamp_IST', 'Symbol', 'State', 'Regime', 
        'Open', 'High', 'Low', 'Close', 'Volume', 
        'Velocity_10m', 'ATR_14', 'Trend_20', 'Would_ACTION', 'Reason'
    ])
    
    state_map = {sym: ReplaySymbolData(sym) for sym in TARGET_ASSETS}
    
    with Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("{task.completed}/{task.total} min"),
    ) as progress:
        replay_task = progress.add_task("Replaying Market...", total=len(sorted_timestamps))
        
        for ts in sorted_timestamps:
            # A. Update Global State (Latest Prices)
            current_prices = {}
            for sym in TARGET_ASSETS:
                candle = data_map.get(sym, {}).get(ts)
                if candle:
                    state_map[sym].update(candle['o'], candle['h'], candle['l'], candle['c'])
                    current_prices[sym] = candle['c']
            
            # B. Detect Regime (Global Median Velocity)
            velocities = []
            for sym in TARGET_ASSETS:
                v = abs(state_map[sym].get_velocity())
                velocities.append(v)
            
            median_vel = sorted(velocities)[len(velocities)//2] if velocities else 0
            regime = MarketRegime.CHOP
            if median_vel < 0.05: regime = MarketRegime.LOW_VOL
            elif median_vel > 0.25: regime = MarketRegime.TRENDING
            
            # C. Process Each Symbol
            for sym in TARGET_ASSETS:
                s_data = state_map[sym]
                candle = data_map.get(sym, {}).get(ts)
                
                # Defaults
                if not candle: continue # Skip if missing data for this minute
                
                velocity = s_data.get_velocity()
                atr = s_data.get_atr()
                trend = s_data.get_trend()
                
                action = "-"
                reason = "-"
                
                # --- LOGIC MOCKUP ---
                # 1. WAIT -> ARM
                if s_data.state == "WAIT":
                    if abs(velocity) > VELOCITY_THRESHOLD and regime != MarketRegime.CHOP:
                        s_data.state = "ARM"
                        s_data.arm_streak = 1
                    else:
                        s_data.arm_streak = 0
                        
                # 2. ARM -> ENTRY
                elif s_data.state == "ARM":
                    if abs(velocity) > VELOCITY_THRESHOLD:
                        s_data.arm_streak += 1
                        if s_data.arm_streak >= ARM_PERSISTENCE:
                            # Trend Check
                            if (velocity > 0 and trend == 1) or (velocity < 0 and trend == -1):
                                s_data.state = "ENTRY"
                                action = "WOULD_ENTER"
                                reason = "Velocity+Trend+Persistence"
                            else:
                                s_data.state = "WAIT"
                                reason = "Trend Mismatch"
                    else:
                        s_data.state = "WAIT"
                        reason = "Velocity Drop"
                        
                # 3. ENTRY -> HOLD (Simulate simplified Hold)
                elif s_data.state == "ENTRY":
                    s_data.state = "HOLD"
                    s_data.entry_price = candle['c']
                    s_data.entry_velocity = velocity
                    
                # 4. HOLD -> EXIT (Simulate Decay/Reversal)
                elif s_data.state == "HOLD":
                    # Simple Decay Check
                    if abs(velocity) < (abs(s_data.entry_velocity) * 0.5):
                        s_data.state = "EXIT"
                        action = "WOULD_EXIT"
                        reason = "Decay"
                    elif (s_data.entry_velocity > 0 and velocity < -0.05):
                        s_data.state = "EXIT"
                        action = "WOULD_EXIT"
                        reason = "Reversal"
                        
                elif s_data.state == "EXIT":
                    s_data.state = "WAIT"

                # Log Row
                csv_writer.writerow([
                    timestamp_to_ist_str(ts),
                    sym,
                    s_data.state,
                    regime,
                    candle['o'], candle['h'], candle['l'], candle['c'], candle['v'],
                    f"{velocity:.4f}",
                    f"{atr:.4f}",
                    trend,
                    action,
                    reason
                ])
                
            progress.advance(replay_task)
            
    csv_file.close()
    console.print(f"[bold green]Done! Log written to {OUTPUT_FILE}[/bold green]")

if __name__ == "__main__":
    run_replay()
