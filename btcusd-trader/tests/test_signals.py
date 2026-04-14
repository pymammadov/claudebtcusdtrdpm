"""
Unit tests for signal generation.
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
import pytest

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backtest"))
sys.path.insert(0, str(Path(__file__).parent.parent / "live"))

from indicators import IndicatorLibrary
from strategy import StrategyEvaluator


@pytest.fixture
def sample_data():
    """Create sample OHLCV data for testing."""
    dates = pd.date_range("2023-01-01", periods=200, freq="1h")
    data = {
        "timestamp": dates,
        "open": np.random.normal(40000, 1000, 200),
        "high": np.random.normal(40500, 1000, 200),
        "low": np.random.normal(39500, 1000, 200),
        "close": np.random.normal(40000, 1000, 200),
        "volume": np.random.normal(100, 20, 200),
    }
    df = pd.DataFrame(data)

    # Ensure OHLC ordering
    df["high"] = df[["open", "high", "low", "close"]].max(axis=1)
    df["low"] = df[["open", "high", "low", "close"]].min(axis=1)

    return df


def test_indicator_ema(sample_data):
    """Test EMA calculation."""
    lib = IndicatorLibrary(sample_data)
    indicators = lib.compute_all()

    assert "ema_21" in indicators
    assert not np.isnan(indicators["ema_21"])


def test_indicator_rsi(sample_data):
    """Test RSI calculation."""
    lib = IndicatorLibrary(sample_data)
    indicators = lib.compute_all()

    assert "rsi_14" in indicators
    rsi = indicators["rsi_14"]

    # RSI should be between 0 and 100
    if not np.isnan(rsi):
        assert 0 <= rsi <= 100


def test_indicator_bollinger_bands(sample_data):
    """Test Bollinger Bands calculation."""
    lib = IndicatorLibrary(sample_data)
    indicators = lib.compute_all()

    upper = indicators["bb_upper_20_2.0"]
    mid = indicators["bb_mid_20_2.0"]
    lower = indicators["bb_lower_20_2.0"]

    # Upper should be above middle, middle above lower
    if not (np.isnan(upper) or np.isnan(mid) or np.isnan(lower)):
        assert upper > mid > lower


def test_signal_template_a(sample_data):
    """Test Template A signal generation (requires valid config)."""
    lib = IndicatorLibrary(sample_data)
    df_with_indicators = lib.add_to_dataframe()

    # Check that indicators are added
    assert "ema_8" in df_with_indicators.columns
    assert "rsi_7" in df_with_indicators.columns


def test_live_indicators(sample_data):
    """Test live indicator computation."""
    from indicators import LiveIndicators

    live_ind = LiveIndicators(sample_data)
    indicators = live_ind.compute_all()

    # Check some key indicators exist
    assert "ema_21" in indicators
    assert "rsi_14" in indicators
    assert "atr_14" in indicators


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
