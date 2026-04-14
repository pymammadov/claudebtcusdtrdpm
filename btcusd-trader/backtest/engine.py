"""
Stage 3a: Vectorized Backtesting Engine
High-performance backtesting with fees, slippage, and position sizing.
"""

import numpy as np
import pandas as pd
from typing import Dict, Tuple, Optional, Callable
from dataclasses import dataclass


@dataclass
class BacktestConfig:
    """Backtesting configuration."""

    maker_fee: float = 0.0004  # 0.04%
    taker_fee: float = 0.0006  # 0.06%
    slippage: float = 0.0004  # 0.04% per side
    risk_per_trade_pct: float = 0.01  # 1%
    max_drawdown_pct: float = 0.20  # 20% max allowed
    max_open_positions: int = 1


@dataclass
class Trade:
    """Single trade record."""

    entry_idx: int
    entry_price: float
    entry_time: pd.Timestamp
    exit_idx: int
    exit_price: float
    exit_time: pd.Timestamp
    direction: str  # "long" or "short"
    size: float  # in units (BTC)
    entry_cost: float  # with fees
    exit_proceeds: float  # after fees
    pnl: float
    pnl_pct: float
    max_drawdown_in_trade: float


class BacktestEngine:
    """Vectorized backtest engine."""

    def __init__(self, df: pd.DataFrame, config: BacktestConfig):
        """
        Initialize backtester.

        Args:
            df: DataFrame with OHLCV + indicators
            config: BacktestConfig
        """
        self.df = df.copy()
        self.config = config
        self.trades: list[Trade] = []
        self.equity_curve = None
        self.metrics = {}

    def backtest(self, signal_func) -> Dict[str, float]:
        """
        Run backtest with given signal function.
        Includes TP/SL exit logic based on ATR.

        Args:
            signal_func: Function(df, idx, mode, direction) -> signal
                        Must have sl_mult and tp_mult attributes

        Returns:
            Dictionary of performance metrics
        """
        n = len(self.df)
        balance = 10000.0
        entry_balance = balance
        position = None
        equity = [balance]

        close_arr = self.df["close"].values
        high_arr  = self.df["high"].values
        low_arr   = self.df["low"].values
        atr_arr   = self.df["atr_14"].values

        for i in range(1, n):
            current_close = close_arr[i]
            current_high  = high_arr[i]
            current_low   = low_arr[i]

            if position is not None:
                direction, entry_price, size, entry_idx_val, tp_price, sl_price = position

                exit_price = None
                if direction == "long":
                    if current_low <= sl_price:
                        exit_price = sl_price
                    elif current_high >= tp_price:
                        exit_price = tp_price
                else:
                    if current_high >= sl_price:
                        exit_price = sl_price
                    elif current_low <= tp_price:
                        exit_price = tp_price

                if exit_price is None:
                    exit_sig = signal_func(self.df, i, mode="exit", direction=direction)
                    if exit_sig > 0:
                        exit_price = current_close * (
                            1 - self.config.slippage if direction == "long"
                            else 1 + self.config.slippage
                        )

                if exit_price is not None:
                    fee = self.config.taker_fee
                    slip = self.config.slippage
                    if direction == "long":
                        exit_price_adj = exit_price * (1 - slip)
                        pnl = size * (exit_price_adj * (1 - fee) - entry_price * (1 + fee))
                    else:
                        exit_price_adj = exit_price * (1 + slip)
                        pnl = size * (entry_price * (1 - fee) - exit_price_adj * (1 + fee))

                    trade = Trade(
                        entry_idx=entry_idx_val,
                        entry_price=entry_price,
                        entry_time=self.df["timestamp"].iloc[entry_idx_val],
                        exit_idx=i,
                        exit_price=exit_price,
                        exit_time=self.df["timestamp"].iloc[i],
                        direction=direction,
                        size=size,
                        entry_cost=size * entry_price * (1 + fee),
                        exit_proceeds=size * exit_price * (1 - fee),
                        pnl=pnl,
                        pnl_pct=pnl / (size * entry_price + 1e-10),
                        max_drawdown_in_trade=0.0,
                    )
                    self.trades.append(trade)
                    balance += pnl
                    position = None

            if position is None:
                entry_signal = signal_func(self.df, i, mode="entry")
                if entry_signal in [1, -1]:
                    direction = "long" if entry_signal == 1 else "short"
                    slip = self.config.slippage
                    entry_price = current_close * (1 + slip if direction == "long" else 1 - slip)

                    atr = atr_arr[i]
                    if np.isnan(atr) or atr <= 0:
                        equity.append(balance)
                        continue

                    risk_amount = balance * self.config.risk_per_trade_pct
                    size = risk_amount / atr

                    sl_mult = getattr(signal_func, 'sl_mult', 1.5)
                    tp_mult = getattr(signal_func, 'tp_mult', 3.0)
                    sl_dist = atr * sl_mult
                    tp_dist = atr * tp_mult

                    if direction == "long":
                        sl_price = entry_price - sl_dist
                        tp_price = entry_price + tp_dist
                    else:
                        sl_price = entry_price + sl_dist
                        tp_price = entry_price - tp_dist

                    entry_cost = size * entry_price * (1 + self.config.taker_fee)
                    if entry_cost <= balance:
                        position = (direction, entry_price, size, i, tp_price, sl_price)
                        balance -= entry_cost

            equity.append(balance)

        self.equity_curve = pd.DataFrame({
            "timestamp": self.df["timestamp"],
            "equity": equity,
        })
        self._calculate_metrics(entry_balance)
        return self.metrics

    def _calculate_metrics(self, initial_balance: float):
        """Calculate performance metrics."""
        if not self.trades:
            self.metrics = {
                "total_return_pct": 0.0,
                "sharpe_ratio": 0.0,
                "profit_factor": 0.0,
                "max_drawdown_pct": 0.0,
                "win_rate": 0.0,
                "trade_count": 0,
                "consecutive_losses": 0,
            }
            return

        # Returns
        equity_vals = self.equity_curve["equity"].values
        returns = np.diff(equity_vals) / equity_vals[:-1]
        total_return = (equity_vals[-1] - initial_balance) / initial_balance

        # Sharpe ratio
        daily_returns = returns[::24]  # Approximate daily
        if len(daily_returns) > 1:
            sharpe = np.mean(daily_returns) / (np.std(daily_returns) + 1e-10) * np.sqrt(252)
        else:
            sharpe = 0.0

        # Profit factor
        wins = sum(t.pnl for t in self.trades if t.pnl > 0)
        losses = abs(sum(t.pnl for t in self.trades if t.pnl < 0))
        profit_factor = wins / (losses + 1e-10) if losses > 0 else 1e10

        # Max drawdown
        cumulative_equity = np.maximum.accumulate(equity_vals)
        drawdowns = (equity_vals - cumulative_equity) / cumulative_equity
        max_drawdown = np.min(drawdowns)

        # Win rate
        winning_trades = sum(1 for t in self.trades if t.pnl > 0)
        win_rate = winning_trades / len(self.trades) if self.trades else 0

        # Consecutive losses
        consecutive_losses = 0
        max_consecutive_losses = 0
        for trade in self.trades:
            if trade.pnl < 0:
                consecutive_losses += 1
                max_consecutive_losses = max(max_consecutive_losses, consecutive_losses)
            else:
                consecutive_losses = 0

        self.metrics = {
            "total_return_pct": total_return * 100,
            "sharpe_ratio": sharpe,
            "profit_factor": profit_factor,
            "max_drawdown_pct": abs(max_drawdown) * 100,
            "win_rate": win_rate,
            "trade_count": len(self.trades),
            "consecutive_losses": max_consecutive_losses,
        }

    def get_equity_curve(self) -> pd.DataFrame:
        """Return equity curve."""
        return self.equity_curve

    def get_trades(self) -> list[Trade]:
        """Return all trades."""
        return self.trades

    def get_metrics(self) -> Dict[str, float]:
        """Return performance metrics."""
        return self.metrics
