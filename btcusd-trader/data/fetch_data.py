"""
Stage 1: Data Collection from Binance Futures API
Fetches BTCUSDT candle data, handles pagination and incremental updates.
"""

import os
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
import requests
import pandas as pd
import numpy as np
from typing import Dict, Tuple

logger = logging.getLogger(__name__)


class BinanceDataFetcher:
    """Fetch and manage BTCUSDT perpetual futures data."""

    BASE_URL = "https://fapi.binance.com/fapi/v1/klines"
    DATA_DIR = Path(__file__).parent.parent / "data" / "raw"
    METADATA_FILE = DATA_DIR / "metadata.json"

    # Binance API limits
    KLINES_LIMIT = 1000  # max candles per request
    REQUEST_TIMEOUT = 10

    # Timeframe mappings
    TIMEFRAMES = {
        "15m": 15,
        "1h": 60,
        "4h": 240,
    }

    def __init__(self):
        """Initialize fetcher and create data directory."""
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.metadata = self._load_metadata()

    def _load_metadata(self) -> Dict:
        """Load or initialize metadata tracking latest fetched timestamp per timeframe."""
        if self.METADATA_FILE.exists():
            with open(self.METADATA_FILE) as f:
                return json.load(f)
        return {tf: {"latest_timestamp": 0} for tf in self.TIMEFRAMES}

    def _save_metadata(self):
        """Persist metadata to disk."""
        with open(self.METADATA_FILE, "w") as f:
            json.dump(self.metadata, f, indent=2)

    def fetch_klines(
        self,
        symbol: str = "BTCUSDT",
        interval: str = "15m",
        start_time: int = None,
        end_time: int = None,
        limit: int = 1000,
    ) -> list:
        """
        Fetch klines from Binance with pagination.

        Args:
            symbol: Trading pair (default BTCUSDT)
            interval: Timeframe (15m, 1h, 4h, etc.)
            start_time: Start timestamp in ms (None = from metadata)
            end_time: End timestamp in ms (None = now)
            limit: Max candles per request

        Returns:
            List of [timestamp, o, h, l, c, v, clt, qav, nt, tbb, tbq, ignore]
        """
        if start_time is None:
            # Continue from last fetch
            start_time = self.metadata.get(interval, {}).get("latest_timestamp", 0)
            if start_time > 0:
                # Start from next candle to avoid duplicates
                start_time += self.TIMEFRAMES[interval] * 60 * 1000

        if end_time is None:
            end_time = int(datetime.utcnow().timestamp() * 1000)

        all_klines = []
        current_start = start_time

        while current_start < end_time:
            try:
                params = {
                    "symbol": symbol,
                    "interval": interval,
                    "startTime": current_start,
                    "endTime": end_time,
                    "limit": limit,
                }

                response = requests.get(
                    self.BASE_URL,
                    params=params,
                    timeout=self.REQUEST_TIMEOUT,
                )
                response.raise_for_status()

                klines = response.json()
                if not klines:
                    break

                all_klines.extend(klines)

                # Next iteration starts after last candle
                current_start = klines[-1][0] + self.TIMEFRAMES[interval] * 60 * 1000

                logger.info(
                    f"Fetched {len(klines)} candles for {symbol} {interval} "
                    f"(from {current_start})"
                )

            except requests.RequestException as e:
                logger.error(f"API request failed: {e}")
                raise

        return all_klines

    def clean_klines(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Clean candle data: remove duplicates, handle gaps, sort.

        Args:
            df: DataFrame with columns [timestamp, o, h, l, c, v, ...]

        Returns:
            Clean DataFrame
        """
        # Rename columns for clarity
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

        # Convert to numeric
        for col in ["open", "high", "low", "close", "volume"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")

        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")

        # Remove duplicates (keep first)
        df = df.drop_duplicates(subset=["timestamp"], keep="first")

        # Sort by timestamp
        df = df.sort_values("timestamp").reset_index(drop=True)

        # Keep only essential columns
        df = df[["timestamp", "open", "high", "low", "close", "volume"]]

        return df

    def update_data(self, timeframe: str = "15m", symbol: str = "BTCUSDT"):
        """
        Fetch new data incrementally and save to parquet.

        Args:
            timeframe: 15m, 1h, 4h
            symbol: BTCUSDT
        """
        logger.info(f"Updating {symbol} {timeframe} data...")

        # Fetch new klines
        klines = self.fetch_klines(symbol=symbol, interval=timeframe)

        if not klines:
            logger.info("No new data fetched")
            return

        # Convert to DataFrame
        df = pd.DataFrame(klines)
        df = self.clean_klines(df)

        # Load existing data if present
        parquet_file = self.DATA_DIR / f"{symbol}_{timeframe}.parquet"
        if parquet_file.exists():
            df_existing = pd.read_parquet(parquet_file)
            df = pd.concat([df_existing, df], ignore_index=True)
            df = df.drop_duplicates(subset=["timestamp"], keep="last")
            df = df.sort_values("timestamp").reset_index(drop=True)

        # Save to parquet
        df.to_parquet(parquet_file, index=False)
        logger.info(f"Saved {len(df)} candles to {parquet_file}")

        # Update metadata
        latest_ts = int(df["timestamp"].iloc[-1].timestamp() * 1000)
        self.metadata[timeframe]["latest_timestamp"] = latest_ts
        self._save_metadata()

    def load_data(self, timeframe: str, symbol: str = "BTCUSDT") -> pd.DataFrame:
        """Load data from parquet file."""
        parquet_file = self.DATA_DIR / f"{symbol}_{timeframe}.parquet"
        if not parquet_file.exists():
            raise FileNotFoundError(f"No data file found: {parquet_file}")

        df = pd.read_parquet(parquet_file)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        return df


def main():
    """Fetch all timeframes."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    fetcher = BinanceDataFetcher()

    for timeframe in ["15m", "1h", "4h"]:
        try:
            fetcher.update_data(timeframe=timeframe)
        except Exception as e:
            logger.error(f"Failed to update {timeframe}: {e}")


if __name__ == "__main__":
    main()
