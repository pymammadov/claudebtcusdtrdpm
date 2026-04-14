"""
Unit tests for model scoring and filtering.
"""

import sys
from pathlib import Path
import pytest
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent / "backtest"))

from scorer import ModelScorer, ModelScore


@pytest.fixture
def sample_results():
    """Create sample backtest results."""
    return [
        {
            "model_id": "MODEL_001",
            "template": "TEMPLATE_A",
            "timeframe": "15m",
            "in_sample_metrics": {
                "sharpe_ratio": 1.5,
                "profit_factor": 2.0,
                "max_drawdown_pct": 10.0,
                "win_rate": 0.55,
                "trade_count": 50,
                "consecutive_losses": 5,
            },
            "out_of_sample_metrics": {
                "sharpe_ratio": 1.2,
                "profit_factor": 1.8,
                "max_drawdown_pct": 12.0,
            },
        },
        {
            "model_id": "MODEL_002",
            "template": "TEMPLATE_A",
            "timeframe": "1h",
            "in_sample_metrics": {
                "sharpe_ratio": 0.8,
                "profit_factor": 1.2,
                "max_drawdown_pct": 25.0,
                "win_rate": 0.45,
                "trade_count": 30,
                "consecutive_losses": 10,
            },
        },
    ]


def test_hard_filter_pass(sample_results):
    """Test hard filter pass."""
    metrics = sample_results[0]["in_sample_metrics"]

    passed, reason = ModelScorer.check_hard_filters(metrics)

    assert passed
    assert reason == ""


def test_hard_filter_fail_sharpe():
    """Test hard filter fail on low Sharpe."""
    metrics = {
        "sharpe_ratio": 0.8,
        "profit_factor": 2.0,
        "max_drawdown_pct": 10.0,
        "trade_count": 50,
        "consecutive_losses": 5,
    }

    passed, reason = ModelScorer.check_hard_filters(metrics)

    assert not passed
    assert "Sharpe" in reason


def test_hard_filter_fail_pf():
    """Test hard filter fail on low profit factor."""
    metrics = {
        "sharpe_ratio": 1.5,
        "profit_factor": 1.2,
        "max_drawdown_pct": 10.0,
        "trade_count": 50,
        "consecutive_losses": 5,
    }

    passed, reason = ModelScorer.check_hard_filters(metrics)

    assert not passed
    assert "PF" in reason


def test_hard_filter_fail_drawdown():
    """Test hard filter fail on high drawdown."""
    metrics = {
        "sharpe_ratio": 1.5,
        "profit_factor": 2.0,
        "max_drawdown_pct": 25.0,
        "trade_count": 50,
        "consecutive_losses": 5,
    }

    passed, reason = ModelScorer.check_hard_filters(metrics)

    assert not passed
    assert "MDD" in reason


def test_oos_filter_pass():
    """Test OOS filter pass."""
    is_metrics = {
        "sharpe_ratio": 1.5,
        "profit_factor": 2.0,
    }

    oos_metrics = {
        "sharpe_ratio": 1.2,
        "profit_factor": 1.5,
    }

    passed, reason = ModelScorer.check_oos_filter(is_metrics, oos_metrics)

    assert passed


def test_oos_filter_fail_sharpe():
    """Test OOS filter fail on Sharpe degradation."""
    is_metrics = {
        "sharpe_ratio": 1.5,
        "profit_factor": 2.0,
    }

    oos_metrics = {
        "sharpe_ratio": 0.9,  # Below 70% of 1.5
        "profit_factor": 1.5,
    }

    passed, reason = ModelScorer.check_oos_filter(is_metrics, oos_metrics)

    assert not passed
    assert "Sharpe" in reason


def test_normalize_metric():
    """Test metric normalization."""
    values = np.array([1.0, 2.0, 3.0, 4.0, 5.0])

    # Middle value should normalize to 0.5
    normalized = ModelScorer.normalize_metric(3.0, "sharpe_ratio", values)

    assert 0.4 < normalized < 0.6


def test_score_models(sample_results):
    """Test model scoring."""
    scores = ModelScorer.score_models(sample_results)

    assert len(scores) == 2

    # First model should pass hard filters
    assert scores[0].passed_hard_filters

    # Second model should fail hard filters
    assert not scores[1].passed_hard_filters


def test_get_winner(sample_results):
    """Test winner selection."""
    scores = ModelScorer.score_models(sample_results)

    winner = ModelScorer.get_winner(scores)

    # Winner should be MODEL_001 (passes filters)
    assert winner is not None
    assert winner.model_id == "MODEL_001"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
