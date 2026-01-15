import os
from datetime import datetime
from typing import Dict, Any, Optional
import threading
import queue
import time
import json
from dotenv import load_dotenv

# Load env vars from .env file
load_dotenv()

# Try importing supabase, handle if missing
try:
    from supabase import create_client, Client
except ImportError:
    Client = Any
    create_client = None

class SupabaseManager:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(SupabaseManager, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
            
        self.url = os.environ.get("SUPABASE_URL")
        # Prefer Service Role Key for backend (manager/engine)
        self.key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_KEY")
        self.client: Optional[Client] = None
        self.enabled = False
        
        if self.url and self.key and create_client:
            try:
                self.client = create_client(self.url, self.key)
                self.enabled = True
                print("[Supabase] Connected.")
            except Exception as e:
                print(f"[Supabase] Connection failed: {e}")
        else:
            if not create_client:
                print("[Supabase] 'supabase' package not installed.")
            else:
                print("[Supabase] Missing SUPABASE_URL or SUPABASE_KEY/SUPABASE_SERVICE_ROLE_KEY env vars.")

        self._initialized = True
        self.log_queue = queue.Queue()
        self.running = False
        self.worker_thread = None

    def start_background_logger(self):
        """Start background thread to push logs."""
        if not self.enabled: return
        self.running = True
        self.worker_thread = threading.Thread(target=self._log_worker, daemon=True)
        self.worker_thread.start()

    def _log_worker(self):
        buffer = []
        last_flush = time.time()
        
        while self.running:
            try:
                # Collect logs with timeout
                try:
                    item = self.log_queue.get(timeout=1.0)
                    buffer.append(item)
                except queue.Empty:
                    pass
                
                # Flush conditions: >10 items or >2 seconds
                now = time.time()
                if buffer and (len(buffer) >= 10 or (now - last_flush) > 2.0):
                    self._flush_logs(buffer)
                    buffer = []
                    last_flush = now
                    
            except Exception as e:
                print(f"[Supabase] Worker error: {e}")
                time.sleep(5)

    def _flush_logs(self, logs: list):
        if not self.client: return
        try:
            self.client.table("logs").insert(logs).execute()
        except Exception as e:
            print(f"[Supabase] Insert logs failed: {e}")

    def create_run(self, metadata: Dict[str, Any]) -> str:
        """Create a new run entry and return run_id."""
        if not self.enabled: return "offline_run"
        try:
            data = {
                "start_time": datetime.utcnow().isoformat(),
                "status": "RUNNING",
                "config": json.dumps(metadata.get('config', {}), default=str),
                "engine_version": metadata.get('version', 'v4'),
                "symbols": metadata.get('symbols', [])
            }
            res = self.client.table("runs").insert(data).execute()
            if res.data:
                return res.data[0]['id']
        except Exception as e:
            print(f"[Supabase] Create run failed: {e}")
        return "offline_run"

    def log_event(self, run_id: str, message: str, level: str = "INFO", data: Dict = None):
        """Queue a log event."""
        if not self.enabled or run_id == "offline_run": return
        
        entry = {
            "run_id": run_id,
            "timestamp": datetime.utcnow().isoformat(),
            "message": message,
            "level": level,
            "data": json.dumps(data) if data else None
        }
        self.log_queue.put(entry)

    def update_run_status(self, run_id: str, status: str, result: Dict = None):
        if not self.enabled or run_id == "offline_run": return
        try:
            payload = {"status": status, "end_time": datetime.utcnow().isoformat() if status in ["COMPLETED", "FAILED", "STOPPED"] else None}
            if result:
                payload["result"] = json.dumps(result)
            self.client.table("runs").update(payload).eq("id", run_id).execute()
        except Exception as e:
            print(f"[Supabase] Update status failed: {e}")

    def log_trade(self, run_id: str, trade_data: Dict):
        """Log a trade execution."""
        if not self.enabled or run_id == "offline_run": return
        try:
            # trade_data should match schema or be adaptable
            payload = {
                "run_id": run_id,
                **trade_data
            }
            # Remove any keys not in schema if necessary/known, for now assume loose coupling or JSON col
            self.client.table("trades").insert(payload).execute()
        except Exception as e:
            print(f"[Supabase] Log trade failed: {e}")

    def log_market_data(self, data: Dict):
        """Log market data (price/volume) for charts."""
        if not self.enabled: return
        try:
            # Expected schema: symbol, price, volume, timestamp, run_id (optional)
            self.client.table("market_data").insert(data).execute()
        except Exception as e:
            # Don't spam stdout for high frequency data errors
            pass

# Singleton accessor
_manager = None
def get_supabase():
    global _manager
    if _manager is None:
        _manager = SupabaseManager()
    return _manager
