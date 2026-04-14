"""
Stage 3c-3e: Model Scoring, Filtering, and Selection
Implements hard filters and overfitting detection.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict


@dataclass
class ModelScore:
    """Score for a single model."""

    model_id: str
    template: str
    timeframe: str
    in_sample_metrics: Dict[str, float]
    out_of_sample_metrics: Optional[Dict[str, float]] = None
    composite_score: float = 0.0
    passed_hard_filters: bool = True
    passed_oos_filter: bool = True
    failure_reason: str = ""


class ModelScorer:
    """Score and filter models."""

    # Hard filter thresholds
    HARD_FILTERS = {
        "min_sharpe": 1.2,
        "min_profit_factor": 1.5,
        "max_drawdown": 20.0,
        "min_trade_count": 40,
        "max_consecutive_losses": 8,
    }

    # Out-of-sample filter ratios
    OOS_FILTERS = {
        "min_sharpe_ratio": 0.70,  # OOS_sharpe >= 0.70 × IS_sharpe
        "min_profit_factor_ratio": 0.65,  # OOS_PF >= 0.65 × IS_PF
    }

    # Scoring weights (normalized 0-1)
    SCORING_WEIGHTS = {
        "sharpe_ratio": 0.35,
        "profit_factor": 0.25,
        "max_drawdown": 0.20,
        "win_rate": 0.10,
        "trade_count": 0.10,
    }

    @staticmethod
    def check_hard_filters(metrics: Dict[str, float]) -> Tuple[bool, str]:
        """
        Check if model passes all hard filters.

        Returns:
            (passed: bool, failure_reason: str)
        """
        if metrics.get("sharpe_ratio", 0) < ModelScorer.HARD_FILTERS["min_sharpe"]:
            return False, f"Sharpe {metrics['sharpe_ratio']:.2f} < {ModelScorer.HARD_FILTERS['min_sharpe']}"

        if metrics.get("profit_factor", 0) < ModelScorer.HARD_FILTERS["min_profit_factor"]:
            return False, f"PF {metrics['profit_factor']:.2f} < {ModelScorer.HARD_FILTERS['min_profit_factor']}"

        if metrics.get("max_drawdown_pct", 100) > ModelScorer.HARD_FILTERS["max_drawdown"]:
            return False, f"MDD {metrics['max_drawdown_pct']:.2f}% > {ModelScorer.HARD_FILTERS['max_drawdown']}%"

        if metrics.get("trade_count", 0) < ModelScorer.HARD_FILTERS["min_trade_count"]:
            return False, f"Trades {metrics['trade_count']} < {ModelScorer.HARD_FILTERS['min_trade_count']}"

        if metrics.get("consecutive_losses", 0) > ModelScorer.HARD_FILTERS["max_consecutive_losses"]:
            return False, f"Max cons. losses {metrics['consecutive_losses']} > {ModelScorer.HARD_FILTERS['max_consecutive_losses']}"

        return True, ""

    @staticmethod
    def check_oos_filter(
        is_metrics: Dict[str, float],
        oos_metrics: Dict[str, float],
    ) -> Tuple[bool, str]:
        """
        Check if model passes out-of-sample filters.

        Returns:
            (passed: bool, failure_reason: str)
        """
        is_sharpe = is_metrics.get("sharpe_ratio", 0)
        oos_sharpe = oos_metrics.get("sharpe_ratio", 0)

        if oos_sharpe < ModelScorer.OOS_FILTERS["min_sharpe_ratio"] * is_sharpe:
            return False, f"OOS Sharpe degradation: {oos_sharpe:.2f} < {ModelScorer.OOS_FILTERS['min_sharpe_ratio'] * is_sharpe:.2f}"

        is_pf = is_metrics.get("profit_factor", 0)
        oos_pf = oos_metrics.get("profit_factor", 0)

        if oos_pf < ModelScorer.OOS_FILTERS["min_profit_factor_ratio"] * is_pf:
            return False, f"OOS PF degradation: {oos_pf:.2f} < {ModelScorer.OOS_FILTERS['min_profit_factor_ratio'] * is_pf:.2f}"

        return True, ""

    @staticmethod
    def normalize_metric(value: float, metric_name: str, all_values: np.ndarray) -> float:
        """
        Normalize metric to 0-1 scale using min-max scaling.
        For drawdown, invert (lower is better).
        """
        if metric_name == "max_drawdown":
            # Invert: lower drawdown is better
            value = -value

        min_val = np.min(all_values)
        max_val = np.max(all_values)
        range_val = max_val - min_val

        if range_val == 0:
            return 0.5

        return (value - min_val) / range_val

    @staticmethod
    def calculate_composite_score(
        metrics: Dict[str, float],
        all_sharpes: np.ndarray,
        all_pfs: np.ndarray,
        all_mdds: np.ndarray,
        all_wrs: np.ndarray,
        all_trades: np.ndarray,
    ) -> float:
        """
        Calculate weighted composite score.

        Score = 0.35 × norm(Sharpe) +
                0.25 × norm(PF) +
                0.20 × norm(1/MDD) +
                0.10 × norm(WR) +
                0.10 × norm(TC)
        """
        norm_sharpe = ModelScorer.normalize_metric(
            metrics["sharpe_ratio"], "sharpe_ratio", all_sharpes
        )
        norm_pf = ModelScorer.normalize_metric(
            metrics["profit_factor"], "profit_factor", all_pfs
        )
        norm_mdd = ModelScorer.normalize_metric(
            1.0 / (metrics["max_drawdown_pct"] / 100 + 0.001),
            "max_drawdown",
            1.0 / (all_mdds / 100 + 0.001),
        )
        norm_wr = ModelScorer.normalize_metric(
            metrics["win_rate"], "win_rate", all_wrs
        )
        norm_tc = ModelScorer.normalize_metric(
            metrics["trade_count"], "trade_count", all_trades
        )

        score = (
            0.35 * norm_sharpe
            + 0.25 * norm_pf
            + 0.20 * norm_mdd
            + 0.10 * norm_wr
            + 0.10 * norm_tc
        )

        return score

    @staticmethod
    def score_models(
        results: List[Dict],
    ) -> List[ModelScore]:
        """
        Score all models and apply filters.

        Args:
            results: List of dicts with model_id, metrics, etc.

        Returns:
            List of ModelScore objects
        """
        scores: List[ModelScore] = []

        # First pass: hard filter check
        passing_results = []
        for result in results:
            passed, reason = ModelScorer.check_hard_filters(result["in_sample_metrics"])

            score = ModelScore(
                model_id=result["model_id"],
                template=result["template"],
                timeframe=result["timeframe"],
                in_sample_metrics=result["in_sample_metrics"],
                passed_hard_filters=passed,
                failure_reason=reason if not passed else "",
            )

            if passed:
                passing_results.append((result, score))
            scores.append(score)

        if not passing_results:
            return scores

        # Second pass: calculate composite scores for passing models
        all_sharpes = np.array([r[0]["in_sample_metrics"]["sharpe_ratio"] for r in passing_results])
        all_pfs = np.array([r[0]["in_sample_metrics"]["profit_factor"] for r in passing_results])
        all_mdds = np.array([r[0]["in_sample_metrics"]["max_drawdown_pct"] for r in passing_results])
        all_wrs = np.array([r[0]["in_sample_metrics"]["win_rate"] for r in passing_results])
        all_trades = np.array([r[0]["in_sample_metrics"]["trade_count"] for r in passing_results])

        for result, score in passing_results:
            composite = ModelScorer.calculate_composite_score(
                result["in_sample_metrics"],
                all_sharpes,
                all_pfs,
                all_mdds,
                all_wrs,
                all_trades,
            )
            score.composite_score = composite

        # Third pass: OOS filter (if available) - keep top 10
        top_10 = sorted(
            [s for s in scores if s.passed_hard_filters],
            key=lambda x: x.composite_score,
            reverse=True,
        )[:10]

        for score in top_10:
            if "out_of_sample_metrics" in [k for k in results if k["model_id"] == score.model_id][0]:
                oos_result = [r for r in results if r["model_id"] == score.model_id][0]
                score.out_of_sample_metrics = oos_result["out_of_sample_metrics"]

                passed_oos, reason = ModelScorer.check_oos_filter(
                    score.in_sample_metrics,
                    score.out_of_sample_metrics,
                )
                score.passed_oos_filter = passed_oos
                if not passed_oos:
                    score.failure_reason = f"OOS: {reason}"

        return scores

    @staticmethod
    def get_winner(scores: List[ModelScore]) -> Optional[ModelScore]:
        """
        Select winner: highest score that passes both hard and OOS filters.
        """
        candidates = [
            s
            for s in scores
            if s.passed_hard_filters and s.passed_oos_filter
        ]

        if not candidates:
            return None

        return max(candidates, key=lambda x: x.composite_score)

    @staticmethod
    def create_leaderboard(scores: List[ModelScore]) -> pd.DataFrame:
        """Create leaderboard DataFrame."""
        rows = []

        for score in sorted(scores, key=lambda x: x.composite_score, reverse=True):
            row = {
                "model_id": score.model_id,
                "template": score.template,
                "timeframe": score.timeframe,
                "composite_score": score.composite_score,
                "sharpe": score.in_sample_metrics.get("sharpe_ratio", 0),
                "profit_factor": score.in_sample_metrics.get("profit_factor", 0),
                "max_drawdown_%": score.in_sample_metrics.get("max_drawdown_pct", 0),
                "win_rate": score.in_sample_metrics.get("win_rate", 0),
                "trade_count": score.in_sample_metrics.get("trade_count", 0),
                "hard_filter_pass": score.passed_hard_filters,
                "oos_filter_pass": score.passed_oos_filter,
                "failure_reason": score.failure_reason,
            }

            if score.out_of_sample_metrics:
                row.update({
                    "oos_sharpe": score.out_of_sample_metrics.get("sharpe_ratio", 0),
                    "oos_profit_factor": score.out_of_sample_metrics.get("profit_factor", 0),
                    "oos_max_drawdown_%": score.out_of_sample_metrics.get("max_drawdown_pct", 0),
                })

            rows.append(row)

        return pd.DataFrame(rows)
