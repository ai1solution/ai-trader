from typing import Dict, Optional, List
import threading
from .models import EngineState, EngineInsights, EngineStatus
from datetime import datetime

class EngineStateStore:
    def __init__(self):
        self._states: Dict[str, EngineState] = {}
        from collections import deque
        self._history: Dict[str, deque] = {} # deque of dicts
        self._lock = threading.RLock()

    def _init_symbol(self, symbol: str):
        with self._lock:
            if symbol not in self._states:
                self._states[symbol] = EngineState(
                    symbol=symbol,
                    status=EngineStatus.STARTING,
                    last_updated=datetime.now()
                )
            if symbol not in self._history:
                from collections import deque
                self._history[symbol] = deque(maxlen=5000)

    def write_status(self, symbol: str, status: EngineStatus, error_msg: Optional[str] = None):
        """Called by Worker to update status."""
        with self._lock:
            self._init_symbol(symbol)
            state = self._states[symbol]
            state.status = status
            state.last_updated = datetime.now()
            if error_msg:
                state.error_msg = error_msg

    def write_insights(self, symbol: str, insights: EngineInsights):
        """Called by Worker to update insights."""
        with self._lock:
            self._init_symbol(symbol)
            state = self._states[symbol]
            # Verify symbol consistency
            if insights.symbol != symbol:
                raise ValueError(f"Symbol mismatch: {symbol} vs {insights.symbol}")
            
            state.insights = insights
            state.last_updated = datetime.now()
            
            # Store simplified history for chart
            # We assume insights.timestamp is ISO string, charts need unix timestamp (seconds)
            # But let's verify format. models.py usually has datetime or str.
            # worker.py sets it to datetime.now().isoformat() usually?
            # actually we can just store the insights object or a subset
            try:
                # Convert ISO to unix if possible, or just store raw
                # Frontend expects: { time: number, value: number }
                # Let's do partial parsing here or let frontend handle it?
                # Safer: store raw, let API decide.
                # But for deque, let's store dict
                ts = datetime.fromisoformat(insights.timestamp).timestamp()
                point = {
                    "time": int(ts), 
                    "value": insights.price
                }
                self._history[symbol].append(point)
            except Exception as e:
                # Fallback if timestamp parsing fails
                pass

    def get_latest(self, symbol: str) -> Optional[EngineState]:
        """Read-only access for API."""
        with self._lock:
            return self._states.get(symbol)

    def get_history(self, symbol: str) -> List[Dict]:
        """Get history points."""
        with self._lock:
            if symbol in self._history:
                return list(self._history[symbol])
            return []

    def get_all_symbols(self) -> List[str]:
        """List all tracked symbols."""
        with self._lock:
            return list(self._states.keys())
