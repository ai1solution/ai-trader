from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import pandas as pd

from v4.engine.regime import RegimeClassifier
from v4.engine.universe import UniverseSelector

router = APIRouter(prefix="/analyze", tags=["analysis"])

class RegimeRequest(BaseModel):
    symbol: str
    date: Optional[str] = None # ISO format

@router.post("/regime")
async def check_regime(req: RegimeRequest):
    """
    Check market regime for a symbol.
    Logic: Instantiates a RegimeClassifier, fetches data, determines regime.
    """
    classifier = RegimeClassifier()
    try:
        # Determine time
        import traceback
        dt = datetime.fromisoformat(req.date) if req.date else datetime.now()
        if dt.tzinfo is None:
            # Assume UTC if naive
            from datetime import timezone
            dt = dt.replace(tzinfo=timezone.utc)
            
        print(f"[Analyze] Checking regime for {req.symbol} at {dt}")
        
        # We need to pre-load data for the classifier to work synchronously (as per new design)
        # Or allow it to fetch if we didn't strictly ban fetch in `get_regime` (we did ban it).
        # Wait, `get_regime` relies on cache or `daily_data`.
        # The stateless API needs to populate this.
        
        # Fetch data for this single symbol
        # Range: Looking back 60 days from target date
        end_dt = dt
        start_dt = dt - pd.Timedelta(days=80)
        
        df = await classifier.provider.fetch_ohlcv(req.symbol, '1d', start_time=start_dt, end_time=end_dt)
        if df is None or df.empty:
             print("[Analyze] No data fetched!")
        else:
             print(f"[Analyze] Fetched {len(df)} rows. Last: {df.iloc[-1]['timestamp']}")
             
        classifier.preload_data(req.symbol, df)
        
        regime = await classifier.get_regime(req.symbol, dt)
        
        return {
            "symbol": req.symbol,
            "date": dt.isoformat(),
            "regime": regime
        }
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await classifier.cleanup()

class UniverseRequest(BaseModel):
    min_volume: float = 1000000.0
    min_price: float = 0.0
    blacklist: List[str] = []

@router.post("/universe")
async def select_universe(req: UniverseRequest):
    """
    Run universe selection logic.
    """
    # Construct dict config as expected by UniverseSelector
    config_dict = {
        'universe': {
            'min_video_24h': req.min_volume, # Typo in key name expectation? code says 'min_volume_24h'
            'min_volume_24h': req.min_volume,
            'min_price': req.min_price,
            'min_atr_pct': 0.02
        }
    }
    
    # We need to handle blacklist manual override if the class logic doesn't support overwrite via config
    # The class sets `self.blacklist` hardcoded but we can modify it.
    
    selector = UniverseSelector(config_dict)
    if req.blacklist:
        selector.blacklist = req.blacklist
    
    # We need a source list of symbols to filter...
    # UniverseSelector.select_symbols implementation?
    # It takes ALL symbols. We need to pass a broad list or let it fetch?
    # Current v4 implementation expects a list of candidates.
    # Let's use a hardcoded default big list or fetch top from CCXT if possible?
    # For now, let's use a list of common pairs.
    
    candidates = [
        "BTC/USDT", "ETH/USDT", "SOL/USDT", "XRP/USDT", "BNB/USDT",
        "ADA/USDT", "DOGE/USDT", "TRX/USDT", "LINK/USDT", "DOT/USDT",
        "MATIC/USDT", "LTC/USDT", "SHIB/USDT", "AVAX/USDT", "UNI/USDT"
    ]
    
    try:
        selected = await selector.select_symbols(candidates)
        return {
            "candidates_count": len(candidates),
            "selected_count": len(selected),
            "selected": selected
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await selector.cleanup()
