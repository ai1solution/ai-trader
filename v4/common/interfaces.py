"""
Abstract interface for market data feeds.
"""
from abc import ABC, abstractmethod
from typing import Optional, AsyncIterator
from datetime import datetime
from .types import Tick

class MarketDataFeed(ABC):
    """
    Abstract base class for a data feed.
    Data can be historical (replay) or live.
    
    Designed to be used in an async loop.
    """
    
    @abstractmethod
    async def get_next_tick(self) -> Optional[Tick]:
        """
        Get the next tick from the feed.
        Returns None if feed is exhausted (historical).
        Should yield control (await) if live and waiting for data.
        """
        pass
    
    @abstractmethod
    def get_current_time(self) -> datetime:
        """
        Get the current 'engine time'.
        For live: returns wall clock UTC.
        For historical: returns current replay time.
        """
        pass
    
    @abstractmethod
    async def cleanup(self):
        """
        Close connections or file handles.
        """
        pass

class DataProvider(ABC):
    """
    Interface for fetching/subscribing to data (The 'Source').
    Used by the Feed to get raw data.
    """
    pass
