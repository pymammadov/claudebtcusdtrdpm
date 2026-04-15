"""
Stage 2a: Indicator Library
Pre-computes all technical indicators for strategy discovery.
Uses vectorized NumPy/Pandas operations for performance.
"""

import numpy as np
import pandas as pd
from typing import Dict, Tuple


class IndicatorLibrary:
    """Compute all technical indicators on OHLCV data."""

    def __init__(self, df: pd.DataFrame):
        """
        Initialize with OHLCV data.

        Args:
            df: DataFrame with columns [timestamp, open, high, low, close, volume]
        """
        self.df = df.copy()
        self.indicators = {}

    def _ema(self, prices: np.ndarray, period: int) -> np.ndarray:
        """Compute Exponential Moving Average."""
        ema = np.full_like(prices, np.nan, dtype=float)
        multiplier = 2 / (period + 1)

        ema[period - 1] = np.mean(prices[: period])
        for i in range(period, len(prices)):
            ema[i] = prices[i] * multiplier + ema[i - 1] * (1 - multiplier)

        return ema

    def _sma(self, prices: np.ndarray, period: int) -> np.ndarray:
        """Compute Simple Moving Average."""
        return pd.Series(prices).rolling(window=period).mean().values

    def _rsi(self, prices: np.ndarray, period: int) -> np.ndarray:
        """Compute Relative Strength Index."""
        deltas = np.diff(prices)
        seed = deltas[: period + 1]

        up = seed[seed >= 0].sum() / period
        down = -seed[seed < 0].sum() / period

        rs = up / down if down != 0 else 0
        rsi = np.full_like(prices, np.nan, dtype=float)
        rsi[period] = 100.0 - 100.0 / (1.0 + rs)

        for i in range(period + 1, len(prices)):
            delta = deltas[i - 1]
            if delta > 0:
                up = (up * (period - 1) + delta) / period
                down = (down * (period - 1)) / period
            else:
                up = (up * (period - 1)) / period
                down = (down * (period - 1) - delta) / period

            rs = up / down if down != 0 else 0
            rsi[i] = 100.0 - 100.0 / (1.0 + rs)

        return rsi

    def _macd(
        self, prices: np.ndarray, fast: int, slow: int, signal: int
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Compute MACD and Signal line."""
        ema_fast = self._ema(prices, fast)
        ema_slow = self._ema(prices, slow)
        macd_line = ema_fast - ema_slow
        signal_line = self._ema(macd_line, signal)
        histogram = macd_line - signal_line

        return macd_line, signal_line, histogram

    def _atr(self, high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int) -> np.ndarray:
        """Compute Average True Range."""
        tr = np.maximum(
            high - low,
            np.maximum(np.abs(high - np.roll(close, 1)), np.abs(low - np.roll(close, 1))),
        )
        tr[0] = high[0] - low[0]
        atr = pd.Series(tr).ewm(span=period, adjust=False).mean().values

        return atr

    def _bollinger_bands(
        self, prices: np.ndarray, period: int, num_std: float
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Compute Bollinger Bands."""
        sma = self._sma(prices, period)
        std = pd.Series(prices).rolling(window=period).std().values
        upper = sma + (std * num_std)
        lower = sma - (std * num_std)

        return upper, sma, lower

    def _keltner_channel(
        self, high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int, mult: float
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Compute Keltner Channel (using EMA and ATR)."""
        center = self._ema(close, period)
        atr = self._atr(high, low, close, period)
        upper = center + (atr * mult)
        lower = center - (atr * mult)

        return upper, center, lower

    def _stochastic(
        self, high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int, smooth: int
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Compute Stochastic Oscillator."""
        lowest_low = pd.Series(low).rolling(window=period).min().values
        highest_high = pd.Series(high).rolling(window=period).max().values

        k = 100 * (close - lowest_low) / (highest_high - lowest_low + 1e-10)
        k_smooth = pd.Series(k).rolling(window=smooth).mean().values
        d_smooth = pd.Series(k_smooth).rolling(window=smooth).mean().values

        return k_smooth, d_smooth

    def _cci(self, high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int) -> np.ndarray:
        """Compute Commodity Channel Index."""
        tp = (high + low + close) / 3
        sma_tp = self._sma(tp, period)
        mad = pd.Series(tp).rolling(window=period).apply(
            lambda x: np.mean(np.abs(x - x.mean()))
        ).values

        cci = (tp - sma_tp) / (0.015 * mad + 1e-10)

        return cci

    def _obv(self, close: np.ndarray, volume: np.ndarray) -> np.ndarray:
        """Compute On-Balance Volume."""
        obv = np.zeros_like(volume, dtype=float)
        obv[0] = volume[0]

        for i in range(1, len(close)):
            if close[i] > close[i - 1]:
                obv[i] = obv[i - 1] + volume[i]
            elif close[i] < close[i - 1]:
                obv[i] = obv[i - 1] - volume[i]
            else:
                obv[i] = obv[i - 1]

        return obv

    def _vwap(self, high: np.ndarray, low: np.ndarray, close: np.ndarray, volume: np.ndarray) -> np.ndarray:
        """
        Compute VWAP (resets at UTC 00:00).
        """
        vwap = np.zeros_like(close, dtype=float)
        tp = (high + low + close) / 3

        # Assume daily reset (simplification for backtesting)
        cumsum_tp_vol = (tp * volume).cumsum()
        cumsum_vol = volume.cumsum()

        vwap = cumsum_tp_vol / (cumsum_vol + 1e-10)

        return vwap

    def _cmf(self, high: np.ndarray, low: np.ndarray, close: np.ndarray, volume: np.ndarray, period: int) -> np.ndarray:
        """Compute Chaikin Money Flow."""
        mfv = ((close - low) - (high - close)) / (high - low + 1e-10) * volume
        cmf = pd.Series(mfv).rolling(window=period).sum().values
        cmf /= pd.Series(volume).rolling(window=period).sum().values + 1e-10

        return cmf

    def compute_all(self) -> Dict[str, np.ndarray]:
        """
        Pre-compute all indicators.

        Returns:
            Dictionary with all indicator arrays keyed by name
        """
        close = self.df["close"].values.copy()
        open_ = self.df["open"].values.copy()
        high = self.df["high"].values.copy()
        low = self.df["low"].values.copy()
        volume = self.df["volume"].values.copy()

        # TREND - EMA
        for period in [8, 13, 21, 34, 50, 89, 200]:
            self.indicators[f"ema_{period}"] = self._ema(close, period)

        # TREND - SMA
        for period in [20, 50, 100, 200]:
            self.indicators[f"sma_{period}"] = self._sma(close, period)

        # TREND - HMA
        for period in [21, 55]:
            # Simple HMA approximation: weighted EMA
            ema_short = self._ema(close, period // 2)
            ema_long = self._ema(close, period)
            self.indicators[f"hma_{period}"] = 2 * ema_short - ema_long

        # MOMENTUM - RSI
        for period in [7, 14, 21]:
            self.indicators[f"rsi_{period}"] = self._rsi(close, period)

        # MOMENTUM - MACD
        for fast, slow, signal in [(12, 26, 9), (5, 13, 1), (8, 17, 9)]:
            macd, sig, hist = self._macd(close, fast, slow, signal)
            self.indicators[f"macd_{fast}_{slow}_{signal}"] = macd
            self.indicators[f"macd_signal_{fast}_{slow}_{signal}"] = sig
            self.indicators[f"macd_hist_{fast}_{slow}_{signal}"] = hist

        # MOMENTUM - Stochastic
        for period, smooth in [(14, 3), (5, 3)]:
            k, d = self._stochastic(high, low, close, period, smooth)
            self.indicators[f"stoch_k_{period}_{smooth}"] = k
            self.indicators[f"stoch_d_{period}_{smooth}"] = d

        # MOMENTUM - CCI
        for period in [14, 20]:
            self.indicators[f"cci_{period}"] = self._cci(high, low, close, period)

        # VOLATILITY - ATR
        for period in [7, 14]:
            self.indicators[f"atr_{period}"] = self._atr(high, low, close, period)

        # VOLATILITY - Bollinger Bands
        for period, num_std in [(20, 2.0), (20, 2.5)]:
            upper, mid, lower = self._bollinger_bands(close, period, num_std)
            self.indicators[f"bb_upper_{period}_{num_std}"] = upper
            self.indicators[f"bb_mid_{period}_{num_std}"] = mid
            self.indicators[f"bb_lower_{period}_{num_std}"] = lower

        # VOLATILITY - Keltner Channel
        for period, mult in [(20, 1.5), (20, 2.0)]:
            upper, center, lower = self._keltner_channel(high, low, close, period, mult)
            self.indicators[f"kc_upper_{period}_{mult}"] = upper
            self.indicators[f"kc_center_{period}_{mult}"] = center
            self.indicators[f"kc_lower_{period}_{mult}"] = lower

        # VOLUME
        self.indicators["obv"] = self._obv(close, volume)
        self.indicators["vwap"] = self._vwap(high, low, close, volume)
        for period in [20]:
            self.indicators[f"cmf_{period}"] = self._cmf(high, low, close, volume, period)

        return self.indicators

    def add_to_dataframe(self) -> pd.DataFrame:
        """Add all computed indicators to DataFrame."""
        if not self.indicators:
            self.compute_all()

        for name, values in self.indicators.items():
            self.df[name] = values

        return self.df
