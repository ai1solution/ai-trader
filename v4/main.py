"""
Main Entry Point v4.
"""
import asyncio
import sys
import sys
import argparse
import logging
import os
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from v4.config.config import load_config
from v4.runner.runner import ParallelRunner
from v4.dashboard.tui import Dashboard
from v4.config.config import load_config
from v4.runner.runner import ParallelRunner
from v4.dashboard.tui import Dashboard
from rich.live import Live

# Windows-specific fix for 'Event loop is closed' RuntimeError
if sys.platform == 'win32':
    import asyncio.proactor_events
    import asyncio.sslproto
    from functools import wraps

    def silence_event_loop_closed(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            try:
                return func(self, *args, **kwargs)
            except RuntimeError as e:
                if str(e) != 'Event loop is closed':
                    raise
        return wrapper

    asyncio.proactor_events._ProactorBasePipeTransport.__del__ = silence_event_loop_closed(asyncio.proactor_events._ProactorBasePipeTransport.__del__)
    asyncio.sslproto._SSLProtocolTransport.__del__ = silence_event_loop_closed(asyncio.sslproto._SSLProtocolTransport.__del__)

def setup_file_logger():
    os.makedirs("logs", exist_ok=True)
    filename = f"logs/v4_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    logging.basicConfig(
        filename=filename,
        level=logging.INFO,
        format='%(asctime)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    return filename

async def main(config_path: str, no_ui: bool = False, overrides: dict = None):
    # 0. Setup File Logging
    log_file = setup_file_logger()
    print(f"Logging to {log_file}")

    # 1. Load Config
    try:
        config = load_config(config_path, overrides)
    except FileNotFoundError:
        print(f"Config file not found: {config_path}")
        return

    # 2. Setup Runner
    runner = ParallelRunner(config)
    await runner.setup()
    
    # 3. Create Dashboard
    dashboard = Dashboard(runner)
    
    # 4. Run Loop
    if no_ui:
        print("Starting runner (No UI)...")
        await runner.run_loop()
    else:
        with Live(dashboard.generate_table(), refresh_per_second=2) as live:
            # We need to run the runner loop concurrently with UI updates
            # But Live context manager blocks main thread? No, it updates in background thread or we update it?
            # Standard pattern: Loop and update live object.
            
            # Fix Race Condition: Set running=True before task starts
            runner.running = True
            task = asyncio.create_task(runner.run_loop())
            
            try:
                while runner.running and not task.done():
                    # Drain logs
                    while not runner.log_queue.empty():
                        try:
                            msg = runner.log_queue.get_nowait()
                            dashboard.add_log(msg)
                            logging.info(msg)
                        except asyncio.QueueEmpty:
                            break
                            
                    live.update(dashboard.create_layout())
                    await asyncio.sleep(0.2)
            except asyncio.CancelledError:
                pass
            finally:
                runner.running = False
                await runner.cleanup()
                # await task # Optional, but good for cleanup
                
    # Summary
    print("\nSession Ended.")
    stats = runner.get_stats()
    for s in stats:
        print(f"{s['symbol']} ({s['strategy']}): ${s['pnl']:.2f}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="v4 Paper Trading Engine")
    parser.add_argument("--config", type=str, default="v4/config.yaml", help="Path to config file")
    parser.add_argument("--no-ui", action="store_true", help="Disable TUI")
    parser.add_argument("--symbols", nargs="+", help="Override symbols list")
    parser.add_argument("--experiment", type=str, choices=['baseline', 'universe', 'regime', 'capital', 'full'], 
                        default='full', help="Research experiment mode")
    
    args = parser.parse_args()
    
    # Map Experiment to Flags
    overrides = {}
    if args.symbols:
        overrides['symbols'] = args.symbols
        
    if args.experiment == 'baseline':
        overrides.update({
            'use_universe': False, 'use_regime': False, 
            'use_portfolio': False, 'use_protection': False
        })
    elif args.experiment == 'universe':
        overrides.update({
            'use_universe': True, 'use_regime': False, 
            'use_portfolio': False, 'use_protection': False
        })
    elif args.experiment == 'regime':
        overrides.update({
            'use_universe': True, 'use_regime': True, 
            'use_portfolio': False, 'use_protection': False
        })
    elif args.experiment == 'capital':
        overrides.update({
            'use_universe': True, 'use_regime': True, 
            'use_portfolio': True, 'use_protection': False
        })
    elif args.experiment == 'full':
        overrides.update({
            'use_universe': True, 'use_regime': True, 
            'use_portfolio': True, 'use_protection': True
        })
    
    try:
        if args.symbols:
            print(f"Override: Trading {len(args.symbols)} symbols: {args.symbols}")
        asyncio.run(main(args.config, args.no_ui, overrides))
    except KeyboardInterrupt:
        print("Stopped by user.")
