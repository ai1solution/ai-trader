from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import logging
import traceback
from api.manager import runner_manager
from v4.config.config import RunnerConfig, StrategyConfig

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v4", tags=["v4"])

class StartRequest(BaseModel):
    mode: str = "paper"  # paper, backtest, live
    symbols: List[str] = ["BTC/USDT"]
    strategies: List[str] = ["momentum"]
    # Optional overrides
    use_regime: bool = True
    use_universe: bool = True
    
@router.post("/start")
async def start_runner(req: StartRequest):
    """
    Start the V4 ParallelRunner in background.
    """
    logger.info(f"Starting V4 runner with request: {req}")
    print(f"[V4 API] Starting runner - Mode: {req.mode}, Symbols: {req.symbols}, Strategies: {req.strategies}")
    
    try:
        # Construct config
        strat_configs = [StrategyConfig(name=s, params={}) for s in req.strategies]
        logger.info(f"Created strategy configs: {strat_configs}")
        
        config = RunnerConfig(
            mode=req.mode,
            symbols=req.symbols,
            strategies=strat_configs,
            use_regime=req.use_regime,
            use_universe=req.use_universe,
            # Default others
            use_portfolio=True,
            use_protection=True
        )
        logger.info(f"Created RunnerConfig: mode={config.mode}, symbols={config.symbols}")
        
        result = await runner_manager.start_runner(config)
        logger.info(f"Runner started successfully: {result}")
        print(f"[V4 API] Runner started: {result}")
        return result
        
    except Exception as e:
        error_msg = f"Failed to start runner: {str(e)}"
        logger.error(error_msg)
        logger.error(f"Traceback: {traceback.format_exc()}")
        print(f"[V4 API] ERROR: {error_msg}")
        print(f"[V4 API] Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=error_msg)

@router.post("/stop")
async def stop_runner():
    """
    Stop the active runner.
    """
    logger.info("Stopping V4 runner")
    print("[V4 API] Stopping runner")
    
    try:
        result = await runner_manager.stop_runner()
        logger.info(f"Runner stopped: {result}")
        print(f"[V4 API] Runner stopped: {result}")
        return result
    except Exception as e:
        error_msg = f"Failed to stop runner: {str(e)}"
        logger.error(error_msg)
        print(f"[V4 API] ERROR: {error_msg}")
        raise HTTPException(status_code=500, detail=error_msg)

@router.get("/status")
def get_status():
    """
    Get current runner status and stats.
    """
    logger.info("Getting V4 status")
    print("[V4 API] Getting status")
    
    try:
        status = runner_manager.get_status()
        print(f"[V4 API] Status: {status['status']}, Stats count: {len(status.get('stats', []))}")
        return status
    except Exception as e:
        error_msg = f"Failed to get status: {str(e)}"
        logger.error(error_msg)
        print(f"[V4 API] ERROR: {error_msg}")
        raise HTTPException(status_code=500, detail=error_msg)
