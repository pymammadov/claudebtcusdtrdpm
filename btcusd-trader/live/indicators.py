"""
Stage 4a: Live Indicators
Compute technical indicators on streaming data.
"""

import numpy as np
import pandas as pd
from typing import Dict, Optional


class LiveIndicators:
    """Compute indicators on live data buffers."""

    def __init__(self, df: pd.DataFrame):
        """
        Initialize with current buffer.

        Args:
            df: DataFrame with OHLCV data
        """
        self.df = df.copy()

    def _ema(self, prices: np.ndarray, period: int) -> float:
        """Compute latest EMA value."""
        if len(prices) < period:
            return np.nan

        ema = np.full_like(prices, np.nan, dtype=float)
        multiplier = 2 / (period + 1)

        ema[period - 1] = np.mean(prices[: period])
        for i in range(period, len(prices)):
            ema[i] = prices[i] * multiplier + ema[i - 1] * (1 - multiplier)

        return ema[-1]

    def _sma(self, prices: np.ndarray, period: int) -> float:
        """Compute latest SMA value."""
        if len(prices) < period:
            return np.nan
        return np.mean(prices[-period:])

    def _rsi(self, prices: np.ndarray, period: int) -> float:
        """Compute latest RSI value."""
        if len(prices) < period + 1:
            return np.nan

        deltas = np.diff(prices[-period - 1:])
        seed = deltas[: period]

        up = np.sum(deltas[deltas > 0][:period]) / period
        down = -np.sum(deltas[deltas < 0][:period]) / period

        rs = up / down if down != 0 else 0
        rsi = 100.0 - 100.0 / (1.0 + rs)

        return rsi

    def _atr(self, high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int) -> float:
        """Compute latest ATR value."""
        if len(high) < period:
            return np.nan

        tr = np.maximum(
            high[-period:] - low[-period:],
            np.maximum(
                np.abs(high[-period:] - np.roll(close, 1)[-period:]),
                np.abs(low[-period:] - np.roll(close, 1)[-period:]),
            ),
        )

        atr = np.mean(tr)
        return atr

    def _bb_bands(
        self, prices: np.ndarray, period: int, num_std: float
    ) -> tuple:
        """Compute Bollinger Bands upper/middle/lower."""
        if len(prices) < period:
            return np.nan, np.nan, np.nan

        sma = np.mean(prices[-period:])
        std = np.std(prices[-period:])

        upper = sma + (std * num_std)
        lower = sma - (std * num_std)

        return upper, sma, lower

    def _macd(
        self, prices: np.ndarray, fast: int, slow: int, signal: int
    ) -> tuple:
        """Compute MACD, signal, and histogram."""
        if len(prices) < slow + signal:
            return np.nan, np.nan, np.nan

        ema_fast = self._ema(prices, fast)
        ema_slow = self._ema(prices, slow)

        if np.isnan(ema_fast) or np.isnan(ema_slow):
            return np.nan, np.nan, np.nan

        macd = ema_fast - ema_slow
        signal_line = self._ema(np.array([macd]), signal)
        histogram = macd - signal_line

        return macd, signal_line, histogram

    def compute_all(self) -> Dict[str, float]:
        """Compute all required indicators for current state."""
        close = self.df["close"].values
        high = self.df["high"].values
        low = self.df["low"].values
        volume = self.df["volume"].values

        indicators = {}

        # Trend indicators
        for period in [8, 13, 21, 34, 50, 89, 200]:
            indicators[f"ema_{period}"] = self._ema(close, period)

        for period in [20, 50, 100, 200]:
            indicators[f"sma_{period}"] = self._sma(close, period)

        # Momentum indicators
        for period in [7, 14, 21]:
            indicators[f"rsi_{period}"] = self._rsi(close, period)

        # Volatility indicators
        for period in [7, 14]:
            indicators[f"atr_{period}"] = self._atr(high, low, close, period)

        # Bollinger Bands
        for period in [20]:
            for std in [2.0, 2.5]:
                upper, mid, lower = self._bb_bands(close, period, std)
                indicators[f"bb_upper_{period}_{std}"] = upper
                indicators[f"bb_mid_{period}_{std}"] = mid
                indicators[f"bb_lower_{period}_{std}"] = lower

        # MACD
        for fast, slow, signal in [(12, 26, 9)]:
            macd, sig, hist = self._macd(close, fast, slow, signal)
            indicators[f"macd_{fast}_{slow}_{signal}"] = macd
            indicators[f"macd_signal_{fast}_{slow}_{signal}"] = sig
            indicators[f"macd_hist_{fast}_{slow}_{signal}"] = hist

        return indicators

    def get_indicator(self, name: str) -> Optional[float]:
        """Get single indicator value."""
        all_ind = self.compute_all()
        return all_ind.get(name)
