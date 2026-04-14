"""
Stage 4a: Live Data Feed
Fetches real-time candles from Binance Futures API and maintains buffer.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List
import aiohttp
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


class LiveDataFeed:
    """Manage live candle data from Binance Futures."""

    BASE_URL = "https://fapi.binance.com/fapi/v1"

    def __init__(self, symbol: str = "BTCUSDT", buffer_size: int = 500):
        """
        Initialize data feed.

        Args:
            symbol: Trading symbol (BTCUSDT)
            buffer_size: Max candles to keep in memory per timeframe
        """
        self.symbol = symbol
        self.buffer_size = buffer_size
        self.buffers = {
            "15m": pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"]),
            "1h": pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"]),
            "4h": pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"]),
        }
        self.last_fetch = {tf: 0 for tf in self.buffers}
        self.session: Optional[aiohttp.ClientSession] = None

    async def connect(self):
        """Create HTTP session."""
        self.session = aiohttp.ClientSession()
        logger.info("Data feed connected")

    async def disconnect(self):
        """Close HTTP session."""
        if self.session:
            await self.session.close()
            logger.info("Data feed disconnected")

    async def fetch_latest_candles(
        self, timeframe: str, limit: int = 10
    ) -> List[Dict]:
        """
        Fetch latest candles from API.

        Args:
            timeframe: 15m, 1h, 4h
            limit: Number of candles to fetch

        Returns:
            List of kline objects
        """
        try:
            params = {
                "symbol": self.symbol,
                "interval": timeframe,
                "limit": limit,
            }

            async with self.session.get(
                f"{self.BASE_URL}/klines",
                params=params,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status != 200:
                    logger.error(f"API error: {resp.status}")
                    return []

                klines = await resp.json()
                return klines

        except asyncio.TimeoutError:
            logger.error("Fetch timeout")
            return []
        except Exception as e:
            logger.error(f"Fetch error: {e}")
            return []

    async def update_buffer(self, timeframe: str):
        """Fetch and update buffer for given timeframe."""
        klines = await self.fetch_latest_candles(timeframe, limit=20)

        if not klines:
            return

        # Convert to DataFrame
        df = pd.DataFrame(klines)
        df.columns = [
            "timestamp",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "close_time",
            "quote_asset_volume",
            "number_of_trades",
            "taker_buy_base",
            "taker_buy_quote",
            "ignore",
        ]

        # Clean
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        for col in ["open", "high", "low", "close", "volume"]:
            df[col] = pd.to_numeric(df[col])

        df = df[["timestamp", "open", "high", "low", "close", "volume"]].copy()

        # Merge with existing buffer
        existing = self.buffers[timeframe]

        if len(existing) > 0:
            # Remove duplicates, keep newer
            combined = pd.concat([existing, df], ignore_index=True)
            combined = combined.drop_duplicates(subset=["timestamp"], keep="last")
        else:
            combined = df

        # Keep only buffer_size latest candles
        combined = combined.tail(self.buffer_size).reset_index(drop=True)

        self.buffers[timeframe] = combined
        self.last_fetch[timeframe] = datetime.utcnow().timestamp()

    async def update_all(self):
        """Update all timeframes."""
        tasks = [self.update_buffer(tf) for tf in self.buffers]
        await asyncio.gather(*tasks)

    def get_buffer(self, timeframe: str) -> pd.DataFrame:
        """Get current buffer for timeframe."""
        return self.buffers[timeframe].copy()

    def get_latest_candle(self, timeframe: str) -> Optional[Dict]:
        """Get latest complete candle."""
        df = self.buffers[timeframe]

        if len(df) < 2:
            return None

        # Last complete candle is second to last
        candle = df.iloc[-2].to_dict()
        return candle

    def get_current_price(self, timeframe: str) -> Optional[float]:
        """Get current close price."""
        candle = self.get_latest_candle(timeframe)
        return candle["close"] if candle else None

    def is_new_candle(self, timeframe: str) -> bool:
        """Check if new candle formed."""
        df = self.buffers[timeframe]

        if len(df) < 2:
            return False

        # New candle if last two timestamps differ
        return df["timestamp"].iloc[-1] != df["timestamp"].iloc[-2]

    async def stream_candles(self, timeframe: str, interval_sec: int = 60):
        """
        Stream candle updates.

        Args:
            timeframe: Which timeframe to update
            interval_sec: Polling interval in seconds
        """
        while True:
            await self.update_buffer(timeframe)
            await asyncio.sleep(interval_sec)
