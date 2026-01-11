from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel
from typing import List
import subprocess
import sys
import os

router = APIRouter(prefix="/legacy", tags=["legacy"])

class V3StartRequest(BaseModel):
    symbols: List[str] = ["BTCUSDT", "ETHUSDT"]
    log_level: str = "INFO"

@router.post("/v3/start")
def start_v3(req: V3StartRequest, background_tasks: BackgroundTasks):
    """
    Launch V3 Mock Trader as a separate subprocess.
    """
    # Construct command
    # python v3/live_mock.py --symbols ...
    
    cmd = [sys.executable, "v3/live_mock.py", "--symbols"] + req.symbols + ["--log-level", req.log_level]
    
    # We launch it as a detached subprocess? 
    # Or keep track of it? API usually should manage lifecycle.
    # For simplicity, we just launch it. Managing interactions with a CLI app via API is hard.
    # Just firing it off.
    
    try:
        # Use Popen to start without waiting
        # In a real system, we'd store the PID.
        subprocess.Popen(cmd, cwd=os.getcwd(), creationflags=subprocess.CREATE_NEW_CONSOLE)
        return {"status": "started", "mode": "v3_subprocess", "command": " ".join(cmd)}
    except Exception as e:
        return {"status": "error", "message": str(e)}
