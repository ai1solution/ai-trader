from fastapi import APIRouter, Query, HTTPException
from typing import List, Optional
from pydantic import BaseModel
import ccxt
from datetime import datetime, timedelta

router = APIRouter(prefix="/market", tags=["Market Data"])

# Initialize exchange
exchange = ccxt.binance()

class OHLCVResponse(BaseModel):
    timestamp: int
    open: float
    high: float
    low: float
    close: float
    volume: float

class PriceResponse(BaseModel):
    symbol: str
    price: float
    change24h: float
    volume24h: float

@router.get("/ohlcv", response_model=List[OHLCVResponse])
async def get_ohlcv(
    symbol: str = Query(..., description="Trading pair (e.g., BTC/USDT)"),
    timeframe: str = Query("1h", description="Timeframe: 1m, 5m, 15m, 1h, 1d"),
    limit: int = Query(100, description="Number of candles")
):
    """Get OHLCV candlestick data for charts"""
    try:
        # Fetch from CCXT
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        
        return [
            OHLCVResponse(
                timestamp=int(candle[0]),
                open=float(candle[1]),
                high=float(candle[2]),
                low=float(candle[3]),
                close=float(candle[4]),
                volume=float(candle[5])
            )
            for candle in ohlcv
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/price/{symbol}", response_model=PriceResponse)
async def get_price(symbol: str):
    """Get current price for a symbol"""
    try:
        ticker = exchange.fetch_ticker(symbol)
        
        return PriceResponse(
            symbol=symbol,
            price=ticker['last'],
            change24h=ticker['percentage'] or 0,
            volume24h=ticker['quoteVolume'] or 0
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class PricesRequest(BaseModel):
    symbols: List[str]

@router.post("/prices", response_model=List[PriceResponse])
async def get_prices(request: PricesRequest):
    """Get prices for multiple symbols"""
    prices = []
    for symbol in request.symbols:
        try:
            ticker = exchange.fetch_ticker(symbol)
            prices.append(PriceResponse(
                symbol=symbol,
                price=ticker['last'],
                change24h=ticker['percentage'] or 0,
                volume24h=ticker['quoteVolume'] or 0
            ))
        except:
            continue
    
    return prices
