"""
Unit tests for risk manager.
"""

import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "live"))

from risk_manager import RiskManager


@pytest.fixture
def risk_manager():
    """Create risk manager instance."""
    return RiskManager(
        initial_balance=1000.0,
        risk_per_trade_pct=1.0,
        max_daily_loss_pct=3.0,
    )


def test_position_size_calculation(risk_manager):
    """Test position sizing logic."""
    entry_price = 40000
    stop_loss = 39000

    size = risk_manager.calculate_position_size(entry_price, stop_loss)

    # Should return positive size
    assert size > 0

    # Size should be reasonable
    assert size < 1.0  # Less than 1 BTC


def test_kill_switch_daily_loss(risk_manager):
    """Test daily loss kill-switch."""
    # Simulate losing 3.5% (triggers kill-switch)
    loss = risk_manager.initial_balance * 0.035

    risk_manager.update_balance(-loss)

    assert risk_manager.kill_switch_triggered
    assert "Daily loss" in risk_manager.kill_switch_reason


def test_kill_switch_drawdown(risk_manager):
    """Test max drawdown kill-switch."""
    # Simulate drawdown > 20%
    drawdown = risk_manager.peak_balance * 0.21

    risk_manager.update_balance(-drawdown)

    assert risk_manager.kill_switch_triggered
    assert "drawdown" in risk_manager.kill_switch_reason


def test_can_open_position(risk_manager):
    """Test position opening check."""
    # Should allow opening initially
    assert risk_manager.can_open_position()

    # After kill-switch, should not allow
    risk_manager.kill_switch_triggered = True
    assert not risk_manager.can_open_position()


def test_register_close_position(risk_manager):
    """Test position registration and closing."""
    assert risk_manager.open_positions == 0

    risk_manager.register_position()
    assert risk_manager.open_positions == 1

    risk_manager.close_position(pnl=10.0)
    assert risk_manager.open_positions == 0


def test_status_reporting(risk_manager):
    """Test risk status reporting."""
    status = risk_manager.get_status()

    assert "balance" in status
    assert "daily_pnl" in status
    assert "drawdown_%" in status
    assert "open_positions" in status


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
