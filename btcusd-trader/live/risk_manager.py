"""
Stage 4c: Risk Manager
Position sizing, drawdown limits, and stop-loss enforcement.
"""

import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class RiskManager:
    """Manage risk: position sizing, drawdown limits, etc."""

    def __init__(
        self,
        initial_balance: float,
        risk_per_trade_pct: float = 1.0,
        max_daily_loss_pct: float = 3.0,
        max_open_positions: int = 1,
        max_drawdown_pct: float = 20.0,
    ):
        """
        Initialize risk manager.

        Args:
            initial_balance: Starting account balance
            risk_per_trade_pct: Risk per trade as % of balance
            max_daily_loss_pct: Max daily loss before kill-switch
            max_open_positions: Max concurrent open positions
            max_drawdown_pct: Max drawdown before halt
        """
        self.initial_balance = initial_balance
        self.current_balance = initial_balance
        self.risk_per_trade_pct = risk_per_trade_pct
        self.max_daily_loss_pct = max_daily_loss_pct
        self.max_open_positions = max_open_positions
        self.max_drawdown_pct = max_drawdown_pct

        self.daily_pnl = 0.0
        self.peak_balance = initial_balance
        self.open_positions = 0

        self.kill_switch_triggered = False
        self.kill_switch_reason = ""

    def update_balance(self, pnl: float):
        """Update balance after trade close."""
        self.current_balance += pnl
        self.daily_pnl += pnl

        self.peak_balance = max(self.peak_balance, self.current_balance)

        # Check kill-switch
        drawdown = (self.peak_balance - self.current_balance) / self.peak_balance * 100
        if drawdown > self.max_drawdown_pct:
            self.kill_switch_triggered = True
            self.kill_switch_reason = f"Max drawdown {drawdown:.2f}% exceeded"

        daily_loss_pct = abs(self.daily_pnl) / self.initial_balance * 100
        if self.daily_pnl < 0 and daily_loss_pct > self.max_daily_loss_pct:
            self.kill_switch_triggered = True
            self.kill_switch_reason = f"Daily loss {daily_loss_pct:.2f}% exceeded"

    def can_open_position(self) -> bool:
        """Check if allowed to open new position."""
        if self.kill_switch_triggered:
            logger.warning(f"Kill-switch active: {self.kill_switch_reason}")
            return False

        if self.open_positions >= self.max_open_positions:
            logger.warning(f"Max open positions ({self.max_open_positions}) reached")
            return False

        return True

    def calculate_position_size(
        self,
        entry_price: float,
        stop_loss_price: float,
        balance_reduction: float = 1.0,
    ) -> float:
        """
        Calculate position size based on ATR and risk.

        Args:
            entry_price: Entry price
            stop_loss_price: Stop loss price
            balance_reduction: Reduce size by this factor (e.g., 0.5 for gap risk)

        Returns:
            Position size in base asset (BTC)
        """
        risk_amount = self.current_balance * (self.risk_per_trade_pct / 100) * balance_reduction
        price_risk = abs(entry_price - stop_loss_price)

        if price_risk == 0:
            logger.warning("Zero price risk, using default size")
            return 0.001  # Minimum size

        size = risk_amount / price_risk

        # Sanity check: don't risk more than account can afford
        max_size = self.current_balance / entry_price * 0.1  # Max 10% of account
        size = min(size, max_size)

        return round(size, 8)

    def register_position(self):
        """Register new open position."""
        self.open_positions += 1
        logger.info(f"Position opened. Open positions: {self.open_positions}")

    def close_position(self, pnl: float):
        """Close position and update state."""
        self.open_positions = max(0, self.open_positions - 1)
        self.update_balance(pnl)
        logger.info(f"Position closed. PnL: {pnl:.2f}. Open positions: {self.open_positions}")

    def reset_daily(self):
        """Reset daily counters."""
        self.daily_pnl = 0.0
        logger.info("Daily counters reset")

    def get_status(self) -> Dict:
        """Get current risk status."""
        drawdown = (self.peak_balance - self.current_balance) / self.peak_balance * 100
        daily_loss_pct = abs(self.daily_pnl) / self.initial_balance * 100

        return {
            "balance": self.current_balance,
            "daily_pnl": self.daily_pnl,
            "daily_loss_%": daily_loss_pct,
            "drawdown_%": drawdown,
            "open_positions": self.open_positions,
            "kill_switch": self.kill_switch_triggered,
            "kill_switch_reason": self.kill_switch_reason,
        }
