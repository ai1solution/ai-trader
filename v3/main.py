"""
Main entry point for the trading engine.

Supports:
- Replay mode: backtest on historical data
- Live mode: real-time trading (placeholder)

Usage:
    python main.py --mode replay --symbol BTCUSDT --data-file data/BTCUSDT_1m.csv --start 2024-01-01 --end 2024-01-02
"""

import argparse
from pathlib import Path
from datetime import datetime

from engine import EngineConfig, run_replay_from_config


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Crypto Trading Engine v3",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run replay on BTCUSDT for 1 day
  python main.py --mode replay --symbol BTCUSDT --data-file data/BTCUSDT_1m.csv --start 2024-01-01 --end 2024-01-02
  
  # Run replay on entire dataset
  python main.py --mode replay --symbol BTCUSDT --data-file data/BTCUSDT_1m.csv
  
  # Run with custom config
  python main.py --mode replay --symbol BTCUSDT --data-file data/BTCUSDT_1m.csv --arm-velocity 0.01
        """
    )
    
    # Mode
    parser.add_argument(
        '--mode',
        type=str,
        choices=['replay', 'live'],
        default='replay',
        help='Execution mode (default: replay)'
    )
    
    # Symbol
    parser.add_argument(
        '--symbol',
        type=str,
        required=True,
        help='Trading symbol (e.g., BTCUSDT)'
    )
    
    # Data file (for replay mode)
    parser.add_argument(
        '--data-file',
        type=str,
        help='Path to historical data file (CSV or Parquet)'
    )
    
    # Date range
    parser.add_argument(
        '--start',
        type=str,
        help='Start date (YYYY-MM-DD)'
    )
    
    parser.add_argument(
        '--end',
        type=str,
        help='End date (YYYY-MM-DD)'
    )
    
    # Config overrides
    parser.add_argument(
        '--arm-velocity',
        type=float,
        help='ARM velocity threshold (default: 0.005)'
    )
    
    parser.add_argument(
        '--arm-persistence',
        type=int,
        help='ARM persistence ticks (default: 5)'
    )
    
    parser.add_argument(
        '--atr-stop',
        type=float,
        help='ATR stop multiplier (default: 2.0)'
    )
    
    parser.add_argument(
        '--log-level',
        type=str,
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='Logging level (default: INFO)'
    )
    
    args = parser.parse_args()
    
    # Create config (apply overrides)
    config = EngineConfig(
        arm_velocity_threshold=args.arm_velocity or 0.005,
        arm_persistence_ticks=args.arm_persistence or 5,
        atr_stop_multiplier=args.atr_stop or 2.0,
        log_level=args.log_level,
    )
    
    print("=" * 80)
    print("CRYPTO TRADING ENGINE v3")
    print("=" * 80)
    print(f"Mode:   {args.mode.upper()}")
    print(f"Symbol: {args.symbol}")
    print()
    print("Configuration:")
    print(config)
    print("=" * 80)
    print()
    
    # Execute based on mode
    if args.mode == 'replay':
        if not args.data_file:
            parser.error("--data-file required for replay mode")
        
        data_path = Path(args.data_file)
        if not data_path.exists():
            parser.error(f"Data file not found: {args.data_file}")
        
        # Run replay
        run_replay_from_config(
            symbol=args.symbol,
            file_path=args.data_file,
            start_date=args.start,
            end_date=args.end,
            config=config
        )
        
    elif args.mode == 'live':
        print("LIVE MODE NOT IMPLEMENTED YET")
        print("This is a placeholder for future live trading.")
        print("Live mode will:")
        print("- Connect to exchange WebSocket")
        print("- Use LiveFeed instead of HistoricalFeed")
        print("- Execute real trades via exchange API")
        print("- Same engine code as replay mode")
        return 1
    
    return 0


if __name__ == '__main__':
    exit(main())
