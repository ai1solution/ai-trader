import asyncio
import sys
import os
import logging

# Add root to path
sys.path.append(os.getcwd())

from engine_api.manager import EngineManager
from engine_api.models import EngineStatus

# Setup logging to console
logging.basicConfig(level=logging.INFO)

async def test_logic():
    print(">>> Initializing Manager")
    manager = EngineManager.get_instance()
    
    print(">>> Starting BTC/USDT Engine")
    try:
        status = await manager.start_engine("BTC/USDT")
        print(f">>> Start Result: {status}")
    except Exception as e:
        print(f"!!! Failed to start: {e}")
        import traceback
        traceback.print_exc()
        return

    print(">>> Waiting 5 seconds for ticks...")
    # We need to manually feed it if we don't have real API credentials or if market is closed
    # But manager has real exchange fetcher. 
    # If no credentials, CCXT binance public API should work for fetch_tickers.
    
    for i in range(5):
        await asyncio.sleep(1)
        state = manager.store.get_latest("BTC/USDT")
        if state:
            print(f"[{i}s] Status: {state.status}")
            if state.insights:
                print(f"    Price: {state.insights.price}")
                print(f"    V1: {state.insights.v1}")
                print(f"    V4: {state.insights.v4}")
        else:
            print(f"[{i}s] No state yet")

    print(">>> Shutting Down")
    await manager.shutdown()

if __name__ == "__main__":
    try:
        if sys.platform == 'win32':
             asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        asyncio.run(test_logic())
    except KeyboardInterrupt:
        pass
