from typing import Dict, List
from .types import MarketRegime, SymbolData

class TechnicalAnalysis:
    @staticmethod
    def calculate_atr(highs: List[float], lows: List[float], closes: List[float], period=14) -> float:
        if len(closes) < period + 1:
            return 0.0
        
        tr_list = []
        for i in range(1, len(closes)):
            h = highs[i]
            l = lows[i]
            c_prev = closes[i-1]
            tr = max(h - l, abs(h - c_prev), abs(l - c_prev))
            tr_list.append(tr)
            
        if not tr_list: return 0.0
        relevant_tr = tr_list[-period:]
        if not relevant_tr: return 0.0
        return sum(relevant_tr) / len(relevant_tr)

class RegimeDetector:
    @staticmethod
    def detect(symbol_data_map: Dict[str, SymbolData], symbol_map: Dict[str, str]) -> MarketRegime:
        velocities = []
        
        for sym, data in symbol_data_map.items():
            if symbol_map.get(sym) != 'MAJOR': continue
            velocities.append(abs(data.get_velocity()))
            
        if not velocities: return MarketRegime.CHOP

        avg_vel = sum(velocities) / len(velocities)
        
        # Simple Logic
        if avg_vel > 0.08:
            return MarketRegime.TRENDING
        elif avg_vel < 0.03:
            return MarketRegime.LOW_VOL
        else:
            return MarketRegime.CHOP
