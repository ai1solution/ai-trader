"""
Configuration Schemas.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any
import yaml

@dataclass
class RiskConfig:
    stop_loss_pct: float = 0.02
    take_profit_pct: float = 0.05
    max_drawdown_pct: float = 0.10

@dataclass
class StrategyConfig:
    name: str # "momentum", "mean_reversion", etc.
    params: Dict[str, Any] = field(default_factory=dict)

@dataclass
class RunnerConfig:
    symbols: List[str]
    strategies: List[StrategyConfig]
    risk: RiskConfig
    mode: str = "paper" # "backtest" or "paper"
    
    # Backtest specific
    start_date: str = "2024-01-01"
    end_date: str = "2024-01-07"
    universe: Dict[str, Any] = field(default_factory=dict)
    
    # Experiment Flags
    use_universe: bool = True
    use_regime: bool = True
    use_portfolio: bool = True
    use_protection: bool = True
    
def load_config(path: str, user_overrides: Dict = None) -> RunnerConfig:
    with open(path, 'r') as f:
        data = yaml.safe_load(f)
        
    if user_overrides:
        data.update(user_overrides)
        
    risk = RiskConfig(**data.get('risk', {}))
    strategies = [StrategyConfig(**s) for s in data.get('strategies', [])]
    
    return RunnerConfig(
        symbols=data.get('symbols', []),
        strategies=strategies,
        risk=risk,
        mode=data.get('mode', 'paper'),
        start_date=data.get('start_date', '2024-01-01'),
        end_date=data.get('end_date', '2024-01-07'),
        universe=data.get('universe', {}),
        use_universe=data.get('use_universe', True),
        use_regime=data.get('use_regime', True),
        use_portfolio=data.get('use_portfolio', True),
        use_protection=data.get('use_protection', True)
    )
