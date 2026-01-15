import logging
from typing import Dict, Any, List
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .manager import EngineManager
from .models import EngineState, EngineStatus
from .news_service import fetch_crypto_news, fetch_trending_crypto_news

# Logging Setup
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="AI Trader Analytics API")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Manager Instance
manager = EngineManager.get_instance()

# --- Request Models ---
class StartRequest(BaseModel):
    symbol: str

# --- Endpoints ---

@app.on_event("shutdown")
async def shutdown_event():
    await manager.shutdown()

@app.get("/coins")
async def get_coins():
    """List supported/active coins."""
    # For MVP, return active ones + some defaults
    active = manager.store.get_all_symbols()
    return {"active": active, "defaults": ["BTC/USDT", "ETH/USDT", "SOL/USDT"]}

@app.post("/engine/start")
async def start_engine(req: StartRequest):
    """Start analysis for a symbol."""
    logging.info(f"Received start command for {req.symbol}")
    try:
        status = await manager.start_engine(req.symbol)
        logging.info(f"Engine start status for {req.symbol}: {status}")
        return {"status": status, "symbol": req.symbol}
    except Exception as e:
        logging.error(f"Failed to start engine for {req.symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/engine/status/{symbol_path:path}")
async def get_status(symbol_path: str):
    """
    Get live state. 
    Note: symbol_path captures 'BTC/USDT' correctly including slash.
    """
    # symbol_path might need decoding if client sends encoded
    symbol = symbol_path 
    state = manager.store.get_latest(symbol)
    
    if not state:
        # If not found but requested, maybe checking if running?
        return {"symbol": symbol, "status": "STOPPED"}
    
    return state

@app.get("/engine/history/{symbol_path:path}")
async def get_history(symbol_path: str):
    """Get historical price data for chart."""
    hist = manager.store.get_history(symbol_path)
    return hist

@app.get("/engine/insights/{symbol_path:path}")
async def get_insights(symbol_path: str):
    """Get just the insights part."""
    state = manager.store.get_latest(symbol_path)
    if not state or not state.insights:
        logging.warning(f"No insights found for {symbol_path}")
        return None # Return null instead of 404 to avoid console red noise
    return state.insights

@app.get("/news")
async def get_news():
    """Get trending crypto market news."""
    try:
        news = await fetch_trending_crypto_news(limit=15)
        return {"news": news, "count": len(news)}
    except Exception as e:
        logging.error(f"Failed to fetch news: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/news/{symbol_path:path}")
async def get_symbol_news(symbol_path: str):
    """Get news specific to a symbol."""
    try:
        news = await fetch_crypto_news(symbol=symbol_path, limit=10)
        return {"symbol": symbol_path, "news": news, "count": len(news)}
    except Exception as e:
        logging.error(f"Failed to fetch symbol news: {e}")
        raise HTTPException(status_code=500, detail=str(e))
