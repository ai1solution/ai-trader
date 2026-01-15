from enum import Enum
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from datetime import datetime

class EngineStatus(str, Enum):
    STARTING = "STARTING"
    RUNNING = "RUNNING"
    STOPPED = "STOPPED"
    ERROR = "ERROR"

class InsightV1(BaseModel):
    state: str
    velocity: float
    trend: str

class InsightV2(BaseModel):
    signal: str
    confidence: float

class InsightV3(BaseModel):
    state: str
    regime: str
    active_strategy: str
    trend: Optional[str] = None  # UP, DOWN, FLAT - aligns with frontend expectations

class InsightV4(BaseModel):
    pnl_projected: Optional[float] = None
    risk_score: Optional[float] = None
    signal: Optional[str] = None

class EngineInsights(BaseModel):
    symbol: str
    timestamp: datetime
    price: float
    v1: Optional[InsightV1] = None
    v2: Optional[InsightV2] = None
    v3: Optional[InsightV3] = None
    v4: Optional[InsightV4] = None

class EngineState(BaseModel):
    symbol: str
    status: EngineStatus
    last_updated: datetime
    error_msg: Optional[str] = None
    insights: Optional[EngineInsights] = None
