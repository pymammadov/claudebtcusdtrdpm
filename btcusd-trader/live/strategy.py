"""
Stage 4a: Strategy Signal Evaluation
Evaluates entry/exit conditions based on winner configuration.
"""

import json
import logging
from typing import Dict, Optional, Tuple
import pandas as pd

from indicators import LiveIndicators

logger = logging.getLogger(__name__)


class StrategyEvaluator:
    """Evaluate strategy signals in real-time."""

    def __init__(self, config_path: str):
        """
        Initialize with winner configuration.

        Args:
            config_path: Path to winner.json
        """
        with open(config_path) as f:
            self.config = json.load(f)

        self.template = self.config["template"]
        self.params = self.config["parameters"]["indicators"]
        self.exit_type = self.config["parameters"]["exit"]

        logger.info(f"Loaded strategy: {self.template} on {self.config['timeframe']}")

    def evaluate_entry(self, df: pd.DataFrame) -> int:
        """
        Evaluate entry signal.

        Args:
            df: Current data buffer (OHLCV)

        Returns:
            1 = long signal, -1 = short signal, 0 = no signal
        """
        if len(df) < 2:
            return 0

        indicators = LiveIndicators(df).compute_all()

        try:
            if self.template == "TEMPLATE_A":
                return self._eval_template_a(indicators)
            elif self.template == "TEMPLATE_B":
                return self._eval_template_b(df, indicators)
            elif self.template == "TEMPLATE_C":
                return self._eval_template_c(df, indicators)
            elif self.template == "TEMPLATE_D":
                return self._eval_template_d(df, indicators)
            elif self.template == "TEMPLATE_E":
                return self._eval_template_e(indicators)
        except Exception as e:
            logger.error(f"Signal evaluation error: {e}")
            return 0

        return 0

    def evaluate_exit(self, df: pd.DataFrame, position_direction: str) -> bool:
        """
        Evaluate exit signal.

        Args:
            df: Current data buffer
            position_direction: "long" or "short"

        Returns:
            True if exit signal triggered
        """
        if self.exit_type == "signal_reversal":
            # Exit when opposite signal forms
            signal = self.evaluate_entry(df)
            if position_direction == "long":
                return signal == -1
            else:
                return signal == 1

        # Other exits handled by price levels (SL/TP)
        return False

    def _eval_template_a(self, indicators: Dict) -> int:
        """Template A: Trend + Momentum."""
        fast_ema = indicators.get(f"ema_{self.params['fast_ema_period']}")
        slow_ema = indicators.get(f"ema_{self.params['slow_ema_period']}")
        rsi = indicators.get(f"rsi_{self.params['rsi_period']}")

        if any(v is None or pd.isna(v) for v in [fast_ema, slow_ema, rsi]):
            return 0

        if fast_ema > slow_ema and rsi < self.params["rsi_threshold_long"]:
            return 1
        if fast_ema < slow_ema and rsi > self.params["rsi_threshold_short"]:
            return -1

        return 0

    def _eval_template_b(self, df: pd.DataFrame, indicators: Dict) -> int:
        """Template B: Bollinger Bands Breakout."""
        close = df["close"].iloc[-1]
        bb_upper = indicators.get(f"bb_upper_{self.params['bb_period']}_{self.params['bb_std_dev']}")
        bb_lower = indicators.get(f"bb_lower_{self.params['bb_period']}_{self.params['bb_std_dev']}")

        if any(v is None or pd.isna(v) for v in [bb_upper, bb_lower]):
            return 0

        volume = df["volume"].iloc[-1]
        volume_sma = df["volume"].tail(20).mean()

        vol_threshold = volume > (volume_sma * self.params["volume_multiplier"])

        if close > bb_upper and vol_threshold:
            return 1
        if close < bb_lower and vol_threshold:
            return -1

        return 0

    def _eval_template_c(self, df: pd.DataFrame, indicators: Dict) -> int:
        """Template C: Mean Reversion."""
        rsi = indicators.get(f"rsi_{self.params['rsi_period']}")
        kc_lower = indicators.get(f"kc_lower_{self.params['kc_period']}_{self.params['kc_mult']}", None)
        close = df["close"].iloc[-1]

        # For live, approximate Keltner Channel
        if kc_lower is None:
            atr = indicators.get(f"atr_{self.params['kc_period']}", 0)
            sma = indicators.get(f"sma_{self.params['kc_period']}", close)
            kc_lower = sma - (atr * self.params['kc_mult'])

        # Using approximate CCI via price deviation
        if any(v is None or pd.isna(v) for v in [rsi, kc_lower]):
            return 0

        if (
            rsi < self.params["rsi_long_threshold"]
            and close < kc_lower
        ):
            return 1

        if (
            rsi > self.params["rsi_short_threshold"]
            and close > kc_lower
        ):
            return -1

        return 0

    def _eval_template_d(self, df: pd.DataFrame, indicators: Dict) -> int:
        """Template D: MACD Cross + Trend Filter."""
        macd_cfg = self.params["macd_config"]
        macd_key = f"macd_{macd_cfg[0]}_{macd_cfg[1]}_{macd_cfg[2]}"
        signal_key = f"macd_signal_{macd_cfg[0]}_{macd_cfg[1]}_{macd_cfg[2]}"

        macd = indicators.get(macd_key)
        signal = indicators.get(signal_key)
        ema_trend = indicators.get(f"ema_{self.params['trend_ema_period']}")
        close = df["close"].iloc[-1]

        if any(v is None or pd.isna(v) for v in [macd, signal, ema_trend]):
            return 0

        if len(df) < 2:
            return 0

        # Check previous values
        prev_close = df["close"].iloc[-2]
        prev_high = df["high"].iloc[-2]
        prev_low = df["low"].iloc[-2]

        # Approximate previous MACD (simplified)
        indicators_prev = LiveIndicators(df.iloc[:-1]).compute_all()
        prev_macd = indicators_prev.get(macd_key, macd)
        prev_signal = indicators_prev.get(signal_key, signal)

        macd_cross_up = (prev_macd <= prev_signal) and (macd > signal)
        macd_cross_down = (prev_macd >= prev_signal) and (macd < signal)

        if macd_cross_up and close > ema_trend:
            return 1
        if macd_cross_down and close < ema_trend:
            return -1

        return 0

    def _eval_template_e(self, indicators: Dict) -> int:
        """Template E: Multi-Timeframe (RSI on lower TF)."""
        rsi = indicators.get(f"rsi_{self.params['lower_tf_rsi_period']}")

        if rsi is None or pd.isna(rsi):
            return 0

        if rsi < self.params["lower_tf_rsi_threshold_long"]:
            return 1
        if rsi > self.params["lower_tf_rsi_threshold_short"]:
            return -1

        return 0

    def get_exit_levels(
        self, entry_price: float, direction: str, atr: float
    ) -> Tuple[float, float]:
        """
        Calculate stop loss and take profit levels.

        Args:
            entry_price: Price at entry
            direction: "long" or "short"
            atr: Current ATR value

        Returns:
            (stop_loss, take_profit)
        """
        exit_config = self.exit_type

        if "fixed_rr" in exit_config:
            ratio = float(exit_config.split("_")[-1])
            # Using 2×ATR as base risk
            risk = atr * 2
            if direction == "long":
                sl = entry_price - risk
                tp = entry_price + (risk * ratio)
            else:
                sl = entry_price + risk
                tp = entry_price - (risk * ratio)

        elif "atr_based" in exit_config:
            sl_mult = 1.5
            tp_mult = 2
            if direction == "long":
                sl = entry_price - (atr * sl_mult)
                tp = entry_price + (atr * tp_mult)
            else:
                sl = entry_price + (atr * sl_mult)
                tp = entry_price - (atr * tp_mult)

        elif "trailing_stop" in exit_config:
            # Trailing stop: SL moves with price
            if direction == "long":
                sl = entry_price - (atr * 1.0)
                tp = entry_price + (atr * 3.0)
            else:
                sl = entry_price + (atr * 1.0)
                tp = entry_price - (atr * 3.0)

        else:
            # Default
            risk = atr * 2
            if direction == "long":
                sl = entry_price - risk
                tp = entry_price + (risk * 2)
            else:
                sl = entry_price + risk
                tp = entry_price - (risk * 2)

        return sl, tp
