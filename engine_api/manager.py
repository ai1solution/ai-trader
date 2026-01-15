import asyncio
import logging
import ccxt.async_support as ccxt
from typing import Dict, List
from concurrent.futures import ThreadPoolExecutor

from .worker import EngineWorker
from .store import EngineStateStore
from .models import EngineStatus

class EngineManager:
    _instance = None

    def __init__(self):
        self.workers: Dict[str, EngineWorker] = {}
        self.store = EngineStateStore()
        self.executor = ThreadPoolExecutor(max_workers=10) # Adjust based on CPU
        self.feed_task = None
        self.exchange = ccxt.binance()
        
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = EngineManager()
        return cls._instance

    async def start_engine(self, symbol: str) -> str:
        if symbol in self.workers:
            worker = self.workers[symbol]
            if worker.status == EngineStatus.RUNNING:
                return "already_running"
            if worker.status in [EngineStatus.STOPPED, EngineStatus.ERROR]:
                # Restart logic could be complex, for MVP just re-instantiate or re-start
                # Re-instantiating is safer to clear old state
                await worker.stop()
        
        # Create new worker
        worker = EngineWorker(symbol, self.store, self.executor)
        self.workers[symbol] = worker
        
        # Start in background
        asyncio.create_task(worker.start())
        
        # Ensure Feed is running
        if not self.feed_task or self.feed_task.done():
            self.feed_task = asyncio.create_task(self._market_feed_loop())
            
        return "started"

    async def _market_feed_loop(self):
        """Fetch prices for all active symbols and dispatch."""
        logging.info("Market Feed Started")
        try:
            while True:
                active_symbols = [
                    sym for sym, w in self.workers.items() 
                    if w.status == EngineStatus.RUNNING or w.status == EngineStatus.STARTING
                ]
                
                if not active_symbols:
                    await asyncio.sleep(1)
                    continue

                try:
                    tickers = await self.exchange.fetch_tickers(active_symbols)
                    for sym, data in tickers.items():
                        if sym in self.workers:
                            # Push to worker queue
                            self.workers[sym].queue.put_nowait(data['last'])
                except Exception as e:
                    logging.error(f"Feed Error: {e}")
                
                await asyncio.sleep(1) # Poll interval
        except asyncio.CancelledError:
            logging.info("Market Feed Stopped")
            await self.exchange.close()

    async def shutdown(self):
        if self.feed_task:
            self.feed_task.cancel()
        for w in self.workers.values():
            await w.stop()
        self.executor.shutdown(wait=False)
        await self.exchange.close()
