"""
Stage 2b: Strategy Templates
Define entry logic templates and generate model configurations.
"""

import itertools
from dataclasses import dataclass, asdict
from typing import Dict, List, Tuple, Any
import pandas as pd
import numpy as np


@dataclass
class StrategyConfig:
    """Complete configuration for a single strategy model."""

    model_id: str
    template: str
    timeframe: str
    parameters: Dict[str, Any]

    def to_dict(self) -> Dict:
        return asdict(self)


class StrategyTemplates:
    """Generate strategy configurations from templates and parameters."""

    # Template A: Trend + Momentum
    TEMPLATE_A = {
        "name": "TEMPLATE_A",
        "description": "Trend + Momentum",
        "parameters": {
            "fast_ema_period": [8, 13, 21],
            "slow_ema_period": [50, 89, 200],
            "rsi_period": [7, 14],
            "rsi_threshold_long": [20, 25, 30],
            "rsi_threshold_short": [70, 75, 80],
        },
        "exit_options": ["fixed_rr_1.5", "fixed_rr_2.0", "atr_based", "trailing_stop"],
    }

    # Template B: Breakout
    TEMPLATE_B = {
        "name": "TEMPLATE_B",
        "description": "Bollinger Bands Breakout",
        "parameters": {
            "bb_period": [20],
            "bb_std_dev": [2.0, 2.5],
            "volume_multiplier": [0.8, 1.0, 1.2],
        },
        "exit_options": ["fixed_rr_2.0", "fixed_rr_2.5", "atr_based", "signal_reversal"],
    }

    # Template C: Mean Reversion
    TEMPLATE_C = {
        "name": "TEMPLATE_C",
        "description": "Mean Reversion",
        "parameters": {
            "rsi_period": [14, 21],
            "rsi_long_threshold": [20, 25, 30],
            "rsi_short_threshold": [70, 75, 80],
            "kc_period": [20],
            "kc_mult": [1.5, 2.0],
            "cci_period": [14, 20],
            "cci_threshold": [80, 100, 120],
        },
        "exit_options": ["fixed_rr_1.5", "fixed_rr_2.0", "signal_reversal"],
    }

    # Template D: MACD Cross + Trend Filter
    TEMPLATE_D = {
        "name": "TEMPLATE_D",
        "description": "MACD Cross with Trend Filter",
        "parameters": {
            "macd_config": [(12, 26, 9), (5, 13, 1), (8, 17, 9)],
            "trend_ema_period": [50, 89, 200],
            "atr_period": [7, 14],
        },
        "exit_options": ["fixed_rr_2.0", "fixed_rr_2.5", "atr_based", "signal_reversal"],
    }

    # Template E: Multi-timeframe
    TEMPLATE_E = {
        "name": "TEMPLATE_E",
        "description": "Multi-Timeframe",
        "parameters": {
            "higher_tf_trend_ema": [50, 89, 200],
            "lower_tf_rsi_period": [14, 21],
            "lower_tf_rsi_threshold_long": [20, 30],
            "lower_tf_rsi_threshold_short": [70, 80],
        },
        "exit_options": ["fixed_rr_1.5", "fixed_rr_2.0", "atr_based"],
    }

    # Exit configurations
    EXIT_CONFIGS = {
        "fixed_rr_1.5": {"type": "fixed_rr", "ratio": 1.5},
        "fixed_rr_2.0": {"type": "fixed_rr", "ratio": 2.0},
        "fixed_rr_2.5": {"type": "fixed_rr", "ratio": 2.5},
        "fixed_rr_3.0": {"type": "fixed_rr", "ratio": 3.0},
        "atr_based": {
            "type": "atr_based",
            "sl_multiplier": [1.0, 1.5, 2.0],
            "tp_ratio": [2, 3],
        },
        "trailing_stop": {"type": "trailing_stop", "atr_multiplier": 1.0},
        "signal_reversal": {"type": "signal_reversal"},
    }

    @staticmethod
    def generate_template_a_configs() -> List[Dict[str, Any]]:
        """Generate all valid TEMPLATE_A configurations."""
        configs = []
        template = StrategyTemplates.TEMPLATE_A

        for (
            fast_ema,
            slow_ema,
            rsi_period,
            rsi_long,
            rsi_short,
            exit_opt,
        ) in itertools.product(
            template["parameters"]["fast_ema_period"],
            template["parameters"]["slow_ema_period"],
            template["parameters"]["rsi_period"],
            template["parameters"]["rsi_threshold_long"],
            template["parameters"]["rsi_threshold_short"],
            template["exit_options"],
        ):
            # Skip invalid: fast >= slow
            if fast_ema >= slow_ema:
                continue
            # Skip invalid: long threshold >= short threshold
            if rsi_long >= rsi_short:
                continue

            configs.append(
                {
                    "template": "TEMPLATE_A",
                    "parameters": {
                        "fast_ema_period": fast_ema,
                        "slow_ema_period": slow_ema,
                        "rsi_period": rsi_period,
                        "rsi_threshold_long": rsi_long,
                        "rsi_threshold_short": rsi_short,
                    },
                    "exit": exit_opt,
                }
            )

        return configs

    @staticmethod
    def generate_template_b_configs() -> List[Dict[str, Any]]:
        """Generate all valid TEMPLATE_B configurations."""
        configs = []
        template = StrategyTemplates.TEMPLATE_B

        for (
            bb_std,
            vol_mult,
            exit_opt,
        ) in itertools.product(
            template["parameters"]["bb_std_dev"],
            template["parameters"]["volume_multiplier"],
            template["exit_options"],
        ):
            configs.append(
                {
                    "template": "TEMPLATE_B",
                    "parameters": {
                        "bb_period": 20,
                        "bb_std_dev": bb_std,
                        "volume_multiplier": vol_mult,
                    },
                    "exit": exit_opt,
                }
            )

        return configs

    @staticmethod
    def generate_template_c_configs() -> List[Dict[str, Any]]:
        """Generate all valid TEMPLATE_C configurations."""
        configs = []
        template = StrategyTemplates.TEMPLATE_C

        for (
            rsi_period,
            rsi_long,
            rsi_short,
            kc_mult,
            cci_period,
            cci_thresh,
            exit_opt,
        ) in itertools.product(
            template["parameters"]["rsi_period"],
            template["parameters"]["rsi_long_threshold"],
            template["parameters"]["rsi_short_threshold"],
            template["parameters"]["kc_mult"],
            template["parameters"]["cci_period"],
            template["parameters"]["cci_threshold"],
            template["exit_options"],
        ):
            if rsi_long >= rsi_short:
                continue

            configs.append(
                {
                    "template": "TEMPLATE_C",
                    "parameters": {
                        "rsi_period": rsi_period,
                        "rsi_long_threshold": rsi_long,
                        "rsi_short_threshold": rsi_short,
                        "kc_period": 20,
                        "kc_mult": kc_mult,
                        "cci_period": cci_period,
                        "cci_threshold": cci_thresh,
                    },
                    "exit": exit_opt,
                }
            )

        return configs

    @staticmethod
    def generate_template_d_configs() -> List[Dict[str, Any]]:
        """Generate all valid TEMPLATE_D configurations."""
        configs = []
        template = StrategyTemplates.TEMPLATE_D

        for (
            macd_config,
            trend_ema,
            atr_period,
            exit_opt,
        ) in itertools.product(
            template["parameters"]["macd_config"],
            template["parameters"]["trend_ema_period"],
            template["parameters"]["atr_period"],
            template["exit_options"],
        ):
            configs.append(
                {
                    "template": "TEMPLATE_D",
                    "parameters": {
                        "macd_config": macd_config,
                        "trend_ema_period": trend_ema,
                        "atr_period": atr_period,
                    },
                    "exit": exit_opt,
                }
            )

        return configs

    @staticmethod
    def generate_template_e_configs() -> List[Dict[str, Any]]:
        """Generate all valid TEMPLATE_E configurations."""
        configs = []
        template = StrategyTemplates.TEMPLATE_E

        for (
            trend_ema,
            rsi_period,
            rsi_long,
            rsi_short,
            exit_opt,
        ) in itertools.product(
            template["parameters"]["higher_tf_trend_ema"],
            template["parameters"]["lower_tf_rsi_period"],
            template["parameters"]["lower_tf_rsi_threshold_long"],
            template["parameters"]["lower_tf_rsi_threshold_short"],
            template["exit_options"],
        ):
            if rsi_long >= rsi_short:
                continue

            configs.append(
                {
                    "template": "TEMPLATE_E",
                    "parameters": {
                        "higher_tf_trend_ema": trend_ema,
                        "lower_tf_rsi_period": rsi_period,
                        "lower_tf_rsi_threshold_long": rsi_long,
                        "lower_tf_rsi_threshold_short": rsi_short,
                    },
                    "exit": exit_opt,
                }
            )

        return configs

    @staticmethod
    def generate_all_configs(timeframes: List[str] = None) -> List[StrategyConfig]:
        """Generate all strategy configurations across all templates and timeframes."""
        if timeframes is None:
            timeframes = ["15m", "1h", "4h"]

        all_configs = []

        # Generate configs from each template
        template_configs = []
        template_configs.extend(StrategyTemplates.generate_template_a_configs())
        template_configs.extend(StrategyTemplates.generate_template_b_configs())
        template_configs.extend(StrategyTemplates.generate_template_c_configs())
        template_configs.extend(StrategyTemplates.generate_template_d_configs())
        template_configs.extend(StrategyTemplates.generate_template_e_configs())

        # Expand by timeframe
        model_id = 0
        for timeframe in timeframes:
            for template_config in template_configs:
                model_id += 1
                config = StrategyConfig(
                    model_id=f"MODEL_{model_id:03d}",
                    template=template_config["template"],
                    timeframe=timeframe,
                    parameters={
                        "indicators": template_config["parameters"],
                        "exit": template_config["exit"],
                    },
                )
                all_configs.append(config)

        return all_configs
