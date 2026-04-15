"""
Orchestrates Stage 2 (Strategy Discovery) and Stage 3 (Validation & Selection).
Generates all models, backtests them, and selects the winner.
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Callable

import pandas as pd
import numpy as np

from indicators import IndicatorLibrary
from templates import StrategyTemplates, StrategyConfig
from engine import BacktestEngine, BacktestConfig
from scorer import ModelScorer, ModelScore

logger = logging.getLogger(__name__)


class StrategyOptimizer:
    """Main optimizer orchestrating the strategy discovery pipeline."""

    def __init__(self, data_dir: Path = None, results_dir: Path = None):
        """
        Initialize optimizer.

        Args:
            data_dir: Path to raw data files
            results_dir: Path to save results
        """
        self.data_dir = data_dir or Path(__file__).parent.parent / "data" / "raw"
        self.results_dir = results_dir or Path(__file__).parent.parent / "results"
        self.results_dir.mkdir(parents=True, exist_ok=True)

        self.log_file = self.results_dir / f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        self._setup_logging()

        self.data = {}  # Cached DataFrames with indicators
        self.backtest_results: List[Dict] = []

    def _setup_logging(self):
        """Setup logging to file and console."""
        handler_file = logging.FileHandler(self.log_file)
        handler_console = logging.StreamHandler()

        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler_file.setFormatter(formatter)
        handler_console.setFormatter(formatter)

        logging.basicConfig(
            level=logging.INFO,
            handlers=[handler_file, handler_console],
        )

    def load_and_prepare_data(self):
        """Load all timeframe data and compute indicators."""
        logger.info("Loading and preparing data...")

        for timeframe in ["15m", "1h", "4h"]:
            try:
                parquet_file = self.data_dir / f"BTCUSDT_{timeframe}.parquet"

                if not parquet_file.exists():
                    logger.warning(f"Data file not found: {parquet_file}")
                    continue

                df = pd.read_parquet(parquet_file)
                df["timestamp"] = pd.to_datetime(df["timestamp"])

                logger.info(f"Loaded {len(df)} candles for {timeframe}")

                # Compute all indicators
                lib = IndicatorLibrary(df)
                df_with_indicators = lib.add_to_dataframe()

                self.data[timeframe] = df_with_indicators
                logger.info(f"Computed indicators for {timeframe}")

            except Exception as e:
                logger.error(f"Failed to load {timeframe}: {e}")

        if not self.data:
            raise RuntimeError("No data loaded!")

        logger.info(f"Data preparation complete: {len(self.data)} timeframes")

    def _get_signal_func(self, config: StrategyConfig) -> Callable:
        """Generate signal function for a given strategy configuration."""

        template = config.template
        params = config.parameters["indicators"]
        exit_cfg = config.parameters["exit"]

        exit_ratios = {
            "fixed_rr_1.5":   (1.5, 2.25),
            "fixed_rr_2.0":   (1.5, 3.0),
            "fixed_rr_2.5":   (1.5, 3.75),
            "fixed_rr_3.0":   (1.5, 4.5),
            "atr_based":      (1.5, 3.0),
            "trailing_stop":  (1.5, 3.0),
            "signal_reversal":(1.5, 3.0),
        }
        sl_mult, tp_mult = exit_ratios.get(exit_cfg, (1.5, 3.0))

        def _get_entry_signal(df, idx):
            if template == "TEMPLATE_A":
                return self._signal_template_a(df, idx, params)
            elif template == "TEMPLATE_B":
                return self._signal_template_b(df, idx, params)
            elif template == "TEMPLATE_C":
                return self._signal_template_c(df, idx, params)
            elif template == "TEMPLATE_D":
                return self._signal_template_d(df, idx, params)
            elif template == "TEMPLATE_E":
                return self._signal_template_e(df, idx, params)
            return 0

        def signal_func(df, idx, mode="entry", direction=None):
            try:
                if mode == "entry":
                    return _get_entry_signal(df, idx)
                elif mode == "exit":
                    if exit_cfg == "signal_reversal":
                        sig = _get_entry_signal(df, idx)
                        if direction == "long" and sig == -1:
                            return 1
                        if direction == "short" and sig == 1:
                            return 1
                    return 0
            except Exception:
                return 0
            return 0

        signal_func.sl_mult = sl_mult
        signal_func.tp_mult = tp_mult
        return signal_func

    def _signal_template_a(self, df: pd.DataFrame, idx: int, params: Dict) -> int:
        """Template A: Trend + Momentum."""
        fast_ema = df[f"ema_{params['fast_ema_period']}"].iloc[idx]
        slow_ema = df[f"ema_{params['slow_ema_period']}"].iloc[idx]
        rsi = df[f"rsi_{params['rsi_period']}"].iloc[idx]

        if pd.isna(fast_ema) or pd.isna(slow_ema) or pd.isna(rsi):
            return 0

        if fast_ema > slow_ema and rsi < params["rsi_threshold_long"]:
            return 1
        if fast_ema < slow_ema and rsi > params["rsi_threshold_short"]:
            return -1

        return 0

    def _signal_template_b(self, df: pd.DataFrame, idx: int, params: Dict) -> int:
        """Template B: Bollinger Bands Breakout."""
        close = df["close"].iloc[idx]
        bb_upper = df[f"bb_upper_{params['bb_period']}_{params['bb_std_dev']}"].iloc[idx]
        bb_lower = df[f"bb_lower_{params['bb_period']}_{params['bb_std_dev']}"].iloc[idx]
        vwap = df["vwap"].iloc[idx]
        volume = df["volume"].iloc[idx]
        volume_sma = df["volume"].rolling(20).mean().iloc[idx]

        if pd.isna(bb_upper) or pd.isna(bb_lower) or pd.isna(vwap):
            return 0

        vol_threshold = volume > (volume_sma * params["volume_multiplier"])

        if close > bb_upper and vol_threshold:
            return 1
        if close < bb_lower and vol_threshold:
            return -1

        return 0

    def _signal_template_c(self, df: pd.DataFrame, idx: int, params: Dict) -> int:
        """Template C: Mean Reversion."""
        rsi = df[f"rsi_{params['rsi_period']}"].iloc[idx]
        kc_lower = df[f"kc_lower_{params['kc_period']}_{params['kc_mult']}"].iloc[idx]
        kc_upper = df[f"kc_upper_{params['kc_period']}_{params['kc_mult']}"].iloc[idx]
        close = df["close"].iloc[idx]
        cci = df[f"cci_{params['cci_period']}"].iloc[idx]

        if pd.isna(rsi) or pd.isna(kc_lower) or pd.isna(cci):
            return 0

        if (
            rsi < params["rsi_long_threshold"]
            and close < kc_lower
            and cci < -params["cci_threshold"]
        ):
            return 1

        if (
            rsi > params["rsi_short_threshold"]
            and close > kc_upper
            and cci > params["cci_threshold"]
        ):
            return -1

        return 0

    def _signal_template_d(self, df: pd.DataFrame, idx: int, params: Dict) -> int:
        """Template D: MACD Cross + Trend Filter."""
        macd_cfg = params["macd_config"]
        macd_key = f"macd_{macd_cfg[0]}_{macd_cfg[1]}_{macd_cfg[2]}"
        signal_key = f"macd_signal_{macd_cfg[0]}_{macd_cfg[1]}_{macd_cfg[2]}"

        macd = df[macd_key].iloc[idx]
        signal = df[signal_key].iloc[idx]
        ema_trend = df[f"ema_{params['trend_ema_period']}"].iloc[idx]
        close = df["close"].iloc[idx]

        if pd.isna(macd) or pd.isna(signal) or pd.isna(ema_trend) or idx < 2:
            return 0

        prev_macd = df[macd_key].iloc[idx - 1]
        prev_signal = df[signal_key].iloc[idx - 1]

        macd_cross_up = (prev_macd <= prev_signal) and (macd > signal)
        macd_cross_down = (prev_macd >= prev_signal) and (macd < signal)

        if macd_cross_up and close > ema_trend:
            return 1
        if macd_cross_down and close < ema_trend:
            return -1

        return 0

    def _signal_template_e(self, df: pd.DataFrame, idx: int, params: Dict) -> int:
        """Template E: Multi-Timeframe (placeholder)."""
        # In real implementation, would load different timeframe data
        # For now, use RSI as entry signal
        rsi = df[f"rsi_{params['lower_tf_rsi_period']}"].iloc[idx]

        if pd.isna(rsi):
            return 0

        if rsi < params["lower_tf_rsi_threshold_long"]:
            return 1
        if rsi > params["lower_tf_rsi_threshold_short"]:
            return -1

        return 0

    def backtest_model(
        self,
        config: StrategyConfig,
        start_date: str = "2020-01-01",
        end_date: str = "2026-04-15",
    ) -> Dict:
        """
        Backtest a single model configuration.

        Args:
            config: StrategyConfig
            start_date: Training start
            end_date: Training end (in-sample period)

        Returns:
            Dictionary with model_id, metrics, etc.
        """
        timeframe = config.timeframe

        if timeframe not in self.data:
            logger.warning(f"Data not available for {timeframe}")
            return None

        df = self.data[timeframe].copy()

        # Filter to training period
        mask = (df["timestamp"] >= start_date) & (df["timestamp"] <= end_date)
        df_train = df[mask].reset_index(drop=True)

        if len(df_train) < 100:
            logger.warning(f"Insufficient data for {config.model_id}")
            return None

        try:
            # Create backtester
            bt_config = BacktestConfig()
            engine = BacktestEngine(df_train, bt_config)

            # Get signal function
            signal_func = self._get_signal_func(config)

            # Run backtest
            metrics = engine.backtest(signal_func)

            # Ensure metrics have all required keys
            for key in ["sharpe_ratio", "profit_factor", "max_drawdown_pct", "win_rate", "trade_count", "consecutive_losses"]:
                if key not in metrics:
                    metrics[key] = 0

            result = {
                "model_id": config.model_id,
                "template": config.template,
                "timeframe": config.timeframe,
                "in_sample_metrics": metrics,
                "config": config.to_dict(),
                "trades": engine.get_trades_as_dicts(),  # Add trades
            }

            logger.info(
                f"{config.model_id}: Sharpe={metrics['sharpe_ratio']:.2f}, "
                f"PF={metrics['profit_factor']:.2f}, MDD={metrics['max_drawdown_pct']:.2f}%, "
                f"Trades={metrics['trade_count']}"
            )

            return result

        except Exception as e:
            logger.error(f"Backtest failed for {config.model_id}: {e}")
            return None

    def backtest_oos(
        self,
        config: StrategyConfig,
        start_date: str = "2023-07-01",
        end_date: str = "2026-04-15",
    ) -> Dict:
        """Backtest on out-of-sample period."""
        timeframe = config.timeframe

        if timeframe not in self.data:
            return None

        df = self.data[timeframe].copy()

        # Filter to OOS period
        mask = (df["timestamp"] >= start_date) & (df["timestamp"] <= end_date)
        df_oos = df[mask].reset_index(drop=True)

        if len(df_oos) < 50:
            return None

        try:
            bt_config = BacktestConfig()
            engine = BacktestEngine(df_oos, bt_config)
            signal_func = self._get_signal_func(config)
            metrics = engine.backtest(signal_func)

            return metrics

        except Exception as e:
            logger.error(f"OOS backtest failed for {config.model_id}: {e}")
            return None

    def run_full_optimization(self):
        """Execute full optimization pipeline."""
        logger.info("=" * 80)
        logger.info("STAGE 2-3: STRATEGY DISCOVERY & VALIDATION")
        logger.info("=" * 80)

        # Load data
        self.load_and_prepare_data()

        # Generate all model configurations
        logger.info("Generating strategy configurations...")
        configs = StrategyTemplates.generate_all_configs()[:100]
        logger.info(f"Generated {len(configs)} unique model configurations")

        # Backtest all models (in-sample)
        logger.info("Running in-sample backtests...")
        for i, config in enumerate(configs):
            if (i + 1) % 50 == 0:
                logger.info(f"Progress: {i+1}/{len(configs)}")

            result = self.backtest_model(config)
            if result:
                self.backtest_results.append(result)

        logger.info(f"Completed in-sample backtests: {len(self.backtest_results)}/{len(configs)} models")

        # Score models
        logger.info("Scoring models...")
        scores = ModelScorer.score_models(self.backtest_results)

        # Run OOS backtest for top 10
        logger.info("Running out-of-sample validation for top 10...")
        top_10 = sorted(
            [s for s in scores if s.passed_hard_filters],
            key=lambda x: x.composite_score,
            reverse=True,
        )[:10]

        for score in top_10:
            # Find original config
            config_dict = next(r["config"] for r in self.backtest_results if r["model_id"] == score.model_id)
            config = StrategyConfig(**config_dict)

            oos_metrics = self.backtest_oos(config)
            if oos_metrics:
                # Update in results
                for result in self.backtest_results:
                    if result["model_id"] == score.model_id:
                        result["out_of_sample_metrics"] = oos_metrics
                        break

        # Re-score with OOS
        scores = ModelScorer.score_models(self.backtest_results)

        # Select winner
        winner = ModelScorer.get_winner(scores)

        if not winner:
            logger.error("No model passed validation!")
            return

        logger.info(f"WINNER: {winner.model_id} ({winner.template} on {winner.timeframe})")
        logger.info(f"Composite Score: {winner.composite_score:.4f}")
        logger.info(f"Sharpe: {winner.in_sample_metrics['sharpe_ratio']:.2f}")
        logger.info(f"Profit Factor: {winner.in_sample_metrics['profit_factor']:.2f}")

        # Save results
        self._save_results(scores, winner)

        logger.info("=" * 80)
        logger.info("Optimization complete!")
        logger.info("=" * 80)

    def _save_results(self, scores: List[ModelScore], winner: ModelScore):
        """Save all results to files."""
        # Leaderboard
        leaderboard = ModelScorer.create_leaderboard(scores)
        leaderboard.to_csv(self.results_dir / "leaderboard.csv", index=False)
        logger.info(f"Saved leaderboard: {self.results_dir / 'leaderboard.csv'}")

        # Find winner result with trades
        winner_result = next(
            r for r in self.backtest_results if r["model_id"] == winner.model_id
        )

        # Winner config with trades
        winner_dict = {
            "model_id": winner.model_id,
            "timeframe": winner.timeframe,
            "template": winner.template,
            "parameters": winner_result["config"]["parameters"],
            "in_sample_metrics": winner.in_sample_metrics,
            "trades": winner_result.get("trades", []),  # Include trades
        }

        if winner.out_of_sample_metrics:
            winner_dict["out_of_sample_metrics"] = winner.out_of_sample_metrics

        with open(self.results_dir / "winner.json", "w") as f:
            json.dump(winner_dict, f, indent=2)
        logger.info(f"Saved winner config: {self.results_dir / 'winner.json'}")

        # Save top 10 models with metrics and trade lists for reporting
        top_10_scores = sorted(
            [s for s in scores if s.passed_hard_filters],
            key=lambda x: x.composite_score,
            reverse=True,
        )[:10]
        top_10_models = []
        for score in top_10_scores:
            result = next(
                (r for r in self.backtest_results if r["model_id"] == score.model_id),
                {},
            )
            top_10_models.append(
                {
                    "model_id": score.model_id,
                    "template": score.template,
                    "timeframe": score.timeframe,
                    "composite_score": score.composite_score,
                    "in_sample_metrics": score.in_sample_metrics,
                    "out_of_sample_metrics": score.out_of_sample_metrics,
                    "trades": result.get("trades", []),
                }
            )

        with open(self.results_dir / "top_10_models.json", "w") as f:
            json.dump(top_10_models, f, indent=2)
        logger.info(f"Saved top 10 models: {self.results_dir / 'top_10_models.json'}")

        # Full summary log
        logger.info(f"Full log: {self.log_file}")


def main():
    """Main entry point."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    optimizer = StrategyOptimizer()

    try:
        optimizer.run_full_optimization()

        # Export results to Windows after optimization completes
        logger.info("Exporting results to Windows...")
        import subprocess
        export_script = Path(__file__).parent.parent.parent / "export_results.sh"
        if export_script.exists():
            try:
                subprocess.run(["bash", str(export_script), "false"], check=False)
                logger.info("✅ Results exported successfully!")
            except Exception as e:
                logger.warning(f"Could not export results: {e}")

    except Exception as e:
        logger.error(f"Optimization failed: {e}", exc_info=True)


if __name__ == "__main__":
    main()
