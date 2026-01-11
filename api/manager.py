import asyncio
from typing import Optional
import logging
import traceback
from v4.runner.runner import ParallelRunner
from v4.config.config import RunnerConfig, StrategyConfig

logger = logging.getLogger(__name__)

class RunnerManager:
    """
    Singleton manager for the V4 ParallelRunner.
    Ensures only one runner is active at a time and manages the background task.
    """
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(RunnerManager, cls).__new__(cls)
            cls._instance.runner: Optional[ParallelRunner] = None
            cls._instance.task: Optional[asyncio.Task] = None
            cls._instance.lock = asyncio.Lock()
        return cls._instance

    async def start_runner(self, config: RunnerConfig):
        logger.info(f"[RunnerManager] start_runner called with mode={config.mode}")
        print(f"[RunnerManager] Starting runner - mode={config.mode}, symbols={config.symbols}")
        
        async with self.lock:
            if self.runner and self.runner.running:
                raise Exception("Runner is already running")
            
            try:
                logger.info("[RunnerManager] Creating ParallelRunner instance")
                print("[RunnerManager] Creating ParallelRunner...")
                self.runner = ParallelRunner(config)
                
                logger.info("[RunnerManager] Calling runner.setup()")
                print("[RunnerManager] Setting up runner...")
                await self.runner.setup()
                
                logger.info("[RunnerManager] Creating background task for run_loop")
                print("[RunnerManager] Starting run loop in background...")
                # Create background task for the run loop
                self.task = asyncio.create_task(self.runner.run_loop())
                
                logger.info("[RunnerManager] Runner started successfully")
                print(f"[RunnerManager] ✓ Runner started: mode={config.mode}")
                return {"status": "started", "config": config.mode}
                
            except Exception as e:
                error_msg = f"Failed to start runner: {str(e)}"
                logger.error(f"[RunnerManager] ERROR: {error_msg}")
                logger.error(f"[RunnerManager] Traceback: {traceback.format_exc()}")
                print(f"[RunnerManager] ERROR: {error_msg}")
                print(f"[RunnerManager] Traceback:\n{traceback.format_exc()}")
                
                # Cleanup on failure
                self.runner = None
                self.task = None
                raise

    async def stop_runner(self):
        logger.info("[RunnerManager] stop_runner called")
        print("[RunnerManager] Stopping runner...")
        
        async with self.lock:
            if not self.runner or not self.runner.running:
                logger.info("[RunnerManager] No runner active")
                print("[RunnerManager] No runner to stop")
                return {"status": "not_running"}
            
            try:
                # Signal stop
                logger.info("[RunnerManager] Signaling runner to stop")
                self.runner.running = False
                
                # Wait for task to finish
                if self.task:
                    try:
                        logger.info("[RunnerManager] Waiting for task to complete")
                        await asyncio.wait_for(self.task, timeout=5.0)
                    except asyncio.TimeoutError:
                        logger.warning("[RunnerManager] Runner stop timed out, forcing cancel")
                        print("[RunnerManager] Stop timeout, forcing cancel...")
                        self.task.cancel()
                    except Exception as e:
                        logger.error(f"[RunnerManager] Error during stop: {e}")
                        print(f"[RunnerManager] Error stopping runner: {e}")
                
                logger.info("[RunnerManager] Cleaning up runner")
                await self.runner.cleanup()
                self.runner = None
                self.task = None
                
                logger.info("[RunnerManager] Runner stopped successfully")
                print("[RunnerManager] ✓ Runner stopped")
                return {"status": "stopped"}
                
            except Exception as e:
                error_msg = f"Error during stop: {str(e)}"
                logger.error(f"[RunnerManager] {error_msg}")
                print(f"[RunnerManager] ERROR: {error_msg}")
                raise

    def get_status(self):
        if not self.runner:
            logger.info("[RunnerManager] Status check: runner is stopped")
            return {"status": "stopped", "stats": []}
        
        try:
            stats = self.runner.get_stats()
            logger.info(f"[RunnerManager] Status check: running with {len(stats)} engines")
            return {
                "status": "running",
                "mode": self.runner.config.mode,
                "stats": stats
            }
        except Exception as e:
            logger.error(f"[RunnerManager] Error getting status: {e}")
            return {"status": "error", "stats": [], "error": str(e)}

runner_manager = RunnerManager()
