import logging
from rich.console import Console

from .types import TradeState, SymbolData, MarketRegime
from .config import SYMBOL_MAP, TARGET_ASSETS
from .strategy import RegimeDetector
from .portfolio import RiskManager, Persistence
from .logger import TrajectoryLogger
from .feed import MarketDataFeed

logger = logging.getLogger("Engine")
console = Console()

class TradingEngine:
    def __init__(self, config, market_feed: MarketDataFeed):
        self.config = config
        self.market_feed = market_feed
        
        # Sub-Systems
        self.risk_manager = RiskManager(config)
        self.persistence = Persistence(config.get("STATE_FILE", "active_trades.json"))
        self.logger = TrajectoryLogger(config.get("TRAJECTORY_FILE", "trajectory.csv"))
        
        # State
        self.symbol_data = {sym: SymbolData(sym) for sym in TARGET_ASSETS}
        self.portfolio = self.persistence.load_portfolio()
        self.market_regime = MarketRegime.CHOP

    def tick(self):
        """
        Executes one engine cycle: Fetch -> Detect -> Process -> Save
        """
        # 1. Fetch Data
        tickers = self.market_feed.get_tickers(TARGET_ASSETS)
        console.print(f"[dim]Tick: {self.market_feed.now()} | {len(tickers)} symbols updated[/dim]", end="\r")
        timestamp_str = "" 
        
        # 2. Update Symbol Data
        for sym, tick in tickers.items():
            if sym in self.symbol_data:
                self.symbol_data[sym].update_price(tick['last'])
                timestamp_str = str(tick.get('timestamp', ''))

        # 3. Detect Regime
        self.market_regime = RegimeDetector.detect(self.symbol_data, SYMBOL_MAP)

        # 4. Process Each Symbol
        curr_time = self.market_feed.now()
        for sym in TARGET_ASSETS:
            self._process_symbol(sym, tickers.get(sym), curr_time, timestamp_str)

        # 5. Persist State
        self.persistence.save_portfolio(self.portfolio)

    def _process_symbol(self, symbol: str, ticker: dict, curr_time: float, timestamp_str: str):
        if not ticker: return
        
        data = self.symbol_data[symbol]
        price = ticker['last']
        velocity = data.get_velocity()
        
        action = "Scanning"
        msg = ""

        # --- Logic Flow ---
        
        # 1. WAIT -> ARM
        if data.state == TradeState.WAIT:
            thresh = self.risk_manager.get_effective_velocity_threshold(symbol)
            if abs(velocity) > thresh:
                data.state = TradeState.ARM
                data.last_arm_time = curr_time
                action = "ARMED"
                msg = f"Vel {velocity:.2f}% > {thresh}%"

        # 2. ARM -> ENTRY
        elif data.state == TradeState.ARM:
            # Immediate Check
            can_enter, reason = self.risk_manager.can_enter(symbol, self.portfolio, self.market_regime)
            if can_enter:
                self._execute_entry(data, price, velocity, curr_time)
                action = "ENTRY"
                msg = "Confirmed"
            else:
                data.state = TradeState.WAIT
                action = "RESET"
                msg = reason

        # 3. HOLD
        elif data.state == TradeState.HOLD:
            action = "HOLD"
            # Manage Position (Check Exit)
            trade = next((t for t in self.portfolio if t['symbol'] == symbol), None)
            if trade:
                # PnL Calc
                pnl = ((price - trade['entry_price']) / trade['entry_price']) * 100
                data.last_trade_pnl = pnl
                msg = f"PnL: {pnl:.2f}%"
                
                if price < trade['stop_loss']:
                    self._close_position(data, trade, price, "STOP_LOSS")
                elif price > trade['take_profit']:
                    self._close_position(data, trade, price, "TAKE_PROFIT")
            else:
                # Fallback if trade missing from portfolio but state is HOLD
                data.state = TradeState.WAIT

        # 4. COOLDOWN (Simple Auto-Reset for now)
        elif data.state == TradeState.COOLDOWN:
            data.state = TradeState.WAIT
            action = "COOLDOWN_DONE"

        # Logging
        self.logger.log_tick(str(timestamp_str or curr_time), {
            'symbol': symbol,
            'state': str(data.state),
            'regime': str(self.market_regime),
            'velocity': velocity,
            'entry_vel': data.entry_velocity,
            'action': action,
            'msg': msg,
            'price': price,
            'ohlcv': {
                'o': ticker.get('open', price), 'h': ticker.get('high', price),
                'l': ticker.get('low', price), 'c': ticker.get('close', price),
                'v': ticker.get('baseVolume', 0)
            } 
        })

    def _execute_entry(self, data: SymbolData, price: float, velocity: float, time_f: float):
        data.state = TradeState.HOLD
        data.entry_price = price
        data.entry_time = time_f
        data.entry_velocity = velocity
        
        trade = {
            "symbol": data.symbol,
            "entry_price": price,
            "size": 1.0, 
            "stop_loss": price * (1 - self.config["STOP_LOSS_PCT"]/100),
            "take_profit": price * (1 + self.config["PROFIT_TARGET_PCT"]/100)
        }
        self.portfolio.append(trade)
        logger.info(f"OPEN LONG {data.symbol} @ {price}")

    def _close_position(self, data: SymbolData, trade: dict, price: float, reason: str):
        logger.info(f"CLOSE {data.symbol} @ {price} ({reason}) PnL: {data.last_trade_pnl:.2f}%")
        if trade in self.portfolio:
            self.portfolio.remove(trade)
        data.state = TradeState.COOLDOWN
