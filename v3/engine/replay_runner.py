"""
Replay runner for historical backtesting.

Loads historical data, creates feeds and engine, runs deterministically.
No time.sleep() - ticks processed as fast as possible.
Engine time ≠ wall-clock time.
"""

import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Optional

from .config import EngineConfig
from .market_data import HistoricalFeed
from .engine import TradingEngine
from .logger import EngineLogger


class ReplayRunner:
    """
    Orchestrates replay mode execution.
    
    Responsibilities:
    - Load historical candle data
    - Create HistoricalFeed (candles → ticks)
    - Create TradingEngine
    - Run tick loop (no delays)
    - Print statistics
    """
    
    def __init__(self, config: EngineConfig, logger: EngineLogger):
        """
        Initialize replay runner.
        
        Args:
            config: Engine configuration
            logger: Logger instance
        """
        self.config = config
        self.logger = logger
        
    def load_data(self, file_path: str, start_date: Optional[str] = None,
                  end_date: Optional[str] = None) -> pd.DataFrame:
        """
        Load historical candle data.
        
        Args:
            file_path: Path to CSV/Parquet file
            start_date: Optional start date filter (ISO format: YYYY-MM-DD)
            end_date: Optional end date filter (ISO format: YYYY-MM-DD)
            
        Returns:
            DataFrame with columns: timestamp, open, high, low, close, volume
            
        Expected CSV format:
            timestamp,open,high,low,close,volume
            2024-01-01 00:00:00,45000.0,45100.0,44900.0,45050.0,1000.0
            ...
        """
        path = Path(file_path)
        
        # Load based on file extension
        if path.suffix == '.csv':
            df = pd.read_csv(file_path)
        elif path.suffix == '.parquet':
            df = pd.read_parquet(file_path)
        else:
            raise ValueError(f"Unsupported file format: {path.suffix}")
        
        # Validate required columns
        required_cols = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            raise ValueError(f"Missing required columns: {missing_cols}")
        
        # Convert timestamp to datetime
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # Ensure UTC timezone
        if df['timestamp'].dt.tz is None:
            df['timestamp'] = df['timestamp'].dt.tz_localize('UTC')
        else:
            df['timestamp'] = df['timestamp'].dt.tz_convert('UTC')
        
        # Filter by date range if provided
        if start_date:
            s_dt = pd.to_datetime(start_date)
            if s_dt.tz is None:
                s_dt = s_dt.tz_localize('UTC')
            df = df[df['timestamp'] >= s_dt]
            
        if end_date:
            e_dt = pd.to_datetime(end_date)
            if e_dt.tz is None:
                e_dt = e_dt.tz_localize('UTC')
            df = df[df['timestamp'] <= e_dt]
        
        # Sort by timestamp
        df = df.sort_values('timestamp').reset_index(drop=True)
        
        # Data quality checks
        if len(df) == 0:
            raise ValueError("No data after filtering")
        
        # Check for NaN values
        if df[required_cols].isnull().any().any():
            self.logger.console_logger.warning("Found NaN values in data, dropping rows")
            df = df.dropna(subset=required_cols)
        
        # Check for negative prices
        if (df[['open', 'high', 'low', 'close']] <= 0).any().any():
            raise ValueError("Found negative or zero prices in data")
        
        # Check OHLC consistency
        invalid_ohlc = (
            (df['high'] < df['low']) |
            (df['high'] < df['open']) |
            (df['high'] < df['close']) |
            (df['low'] > df['open']) |
            (df['low'] > df['close'])
        )
        if invalid_ohlc.any():
            self.logger.console_logger.warning(f"Found {invalid_ohlc.sum()} invalid OHLC candles, dropping")
            df = df[~invalid_ohlc]
        
        return df
    
    def run_replay(self, symbol: str, file_path: str, 
                   start_date: Optional[str] = None,
                   end_date: Optional[str] = None):
        """
        Run replay on historical data.
        
        Args:
            symbol: Trading pair (e.g., "BTCUSDT")
            file_path: Path to historical data file
            start_date: Optional start date (YYYY-MM-DD)
            end_date: Optional end date (YYYY-MM-DD)
        """
        # Load data
        self.logger.console_logger.info(f"Loading data from {file_path}...")
        candles_df = self.load_data(file_path, start_date, end_date)
        
        num_candles = len(candles_df)
        data_start = candles_df['timestamp'].min()
        data_end = candles_df['timestamp'].max()
        
        self.logger.log_replay_start(
            symbol=symbol,
            start_date=data_start.isoformat(),
            end_date=data_end.isoformat(),
            num_candles=num_candles
        )
        
        # Create feed
        self.logger.console_logger.info(f"Creating historical feed...")
        feed = HistoricalFeed(
            candles_df=candles_df,
            tick_interval_seconds=self.config.replay_tick_interval_seconds
        )
        
        # Create engine
        self.logger.console_logger.info(f"Initializing trading engine...")
        engine = TradingEngine(
            symbol=symbol,
            config=self.config,
            logger=self.logger
        )
        
        # Run replay loop (deterministic, no delays)
        self.logger.console_logger.info(f"Starting replay loop...")
        
        start_time = datetime.now()
        tick_count = 0
        
        while feed.has_more_data():
            tick = feed.get_next_tick()
            if tick is None:
                break
                
            engine.on_tick(tick)
            tick_count += 1
            
            # Progress update every 1000 ticks
            if tick_count % 1000 == 0:
                self.logger.console_logger.info(f"Processed {tick_count} ticks...")
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # Get final stats
        stats = engine.get_statistics()
        
        self.logger.log_replay_end(
            total_ticks=tick_count,
            total_trades=stats['trade_count'],
            duration_seconds=duration
        )
        
        # Print summary
        self._print_statistics(stats, tick_count, duration)
        
        # Return stats for programmatic use
        stats['total_ticks'] = tick_count
        stats['duration_seconds'] = duration
        return stats
    
    def _print_statistics(self, stats: dict, total_ticks: int, duration_seconds: float):
        """
        Print replay statistics to console.
        
        Args:
            stats: Engine statistics
            total_ticks: Total ticks processed
            duration_seconds: Replay duration
        """
        print("\n" + "=" * 60)
        print("REPLAY STATISTICS")
        print("=" * 60)
        print(f"Total Ticks:       {total_ticks:,}")
        print(f"Total Trades:      {stats['trade_count']}")
        print(f"Final State:       {stats['current_state']}")
        print(f"In Position:       {stats['is_in_position']}")
        print(f"Replay Duration:   {duration_seconds:.2f}s")
        print(f"Ticks/Second:      {total_ticks / duration_seconds:,.0f}")
        print("=" * 60)
        print("\nFor detailed trade analysis, see logs/engine.log")
        print("To analyze PnL, parse JSON logs with: python -m json.tool logs/engine.log")
        print()


def run_replay_from_config(symbol: str, file_path: str,
                           start_date: Optional[str] = None,
                           end_date: Optional[str] = None,
                           config: Optional[EngineConfig] = None):
    """
    Convenience function to run replay.
    
    Args:
        symbol: Trading pair
        file_path: Path to data file
        start_date: Optional start date
        end_date: Optional end date
        config: Optional config (uses default if None)
    """
    if config is None:
        from .config import DEFAULT_CONFIG
        config = DEFAULT_CONFIG
    
    # Create logger
    logger = EngineLogger(
        log_file=config.log_file,
        log_level=config.log_level
    )
    
    # Log config
    logger.log_config(config.to_dict())
    
    # Create and run replay runner
    runner = ReplayRunner(config, logger)
    stats = runner.run_replay(symbol, file_path, start_date, end_date)
    
    # Close logger
    logger.close()
    
    return stats
