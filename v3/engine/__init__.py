"""
Crypto Trading Engine v3

A deterministic trading engine with strict state machine discipline.

Modules:
- config: Configuration parameters
- enums: Type-safe enums for states, signals, regimes
- market_data: Market data abstraction (live/replay/API)
- indicators: Pure indicator functions (velocity, ATR, regime)
- state: State machine (WAIT → ARM → ENTRY → HOLD → EXIT → COOLDOWN)
- engine: Core trading engine
- logger: Structured logging
- replay_runner: Replay mode orchestration
- api_client: Exchange API client (Binance)

Key principles:
- Correctness over profit
- Deterministic execution
- Explicit state transitions
- Comprehensive logging
"""

__version__ = "3.1.0"  # v3.1: Partial profit-taking + API data feeds

from .config import EngineConfig, DEFAULT_CONFIG
from .enums import TradingState, SignalType, ExitReason, Regime
from .market_data import MarketDataFeed, HistoricalFeed, LiveFeed, Tick
from .market_data import HistoricalAPIDataFeed, LiveAPIDataFeed
from .state import StateMachine, StateContext
from .engine import TradingEngine, Position
from .logger import EngineLogger
from .replay_runner import ReplayRunner, run_replay_from_config

__all__ = [
    # Config
    'EngineConfig',
    'DEFAULT_CONFIG',
    
    # Enums
    'TradingState',
    'SignalType',
    'ExitReason',
    'Regime',
    
    # Market Data
    'MarketDataFeed',
    'HistoricalFeed',
    'LiveFeed',
    'HistoricalAPIDataFeed',
    'LiveAPIDataFeed',
    'Tick',
    
    # State Machine
    'StateMachine',
    'StateContext',
    
    # Engine
    'TradingEngine',
    'Position',
    
    # Logger
    'EngineLogger',
    
    # Replay
    'ReplayRunner',
    'run_replay_from_config',
]
