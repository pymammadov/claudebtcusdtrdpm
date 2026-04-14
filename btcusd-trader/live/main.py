"""
Stage 4: Live Trading Bot
Main orchestrator for live paper/live trading.
"""

import asyncio
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import yaml

from data_feed import LiveDataFeed
from strategy import StrategyEvaluator
from risk_manager import RiskManager
from executor import OrderExecutor
from monitor import HealthMonitor, APIFailureHandler
from journal import TradeJournal

logger = logging.getLogger(__name__)


class LiveTradingBot:
    """Main trading bot orchestrator."""

    def __init__(self, config_path: str = "config.yaml", winner_path: str = "results/winner.json"):
        """
        Initialize bot.

        Args:
            config_path: Path to config.yaml
            winner_path: Path to winner.json
        """
        self.config_path = Path(config_path)
        self.winner_path = Path(winner_path)

        # Load configs
        self.config = self._load_yaml(self.config_path)
        self.symbol = self.config.get("symbol", "BTCUSDT")
        self.timeframe = self.config.get("timeframe", "15m")
        self.paper_trading = self.config.get("paper_trading", True)

        # Components
        self.data_feed = None
        self.strategy = None
        self.risk_manager = None
        self.executor = None
        self.monitor = None
        self.journal = None

        self.running = False
        self.current_position = None  # (order_id, direction)
        self.last_signal_time = None

        logger.info(f"Bot initialized (paper_trading={self.paper_trading})")

    def _load_yaml(self, path: Path) -> dict:
        """Load YAML config with env var substitution."""
        with open(path) as f:
            content = f.read()

        # Replace ${VAR_NAME} with env vars
        for key, value in os.environ.items():
            content = content.replace(f"${{{key}}}", value)

        return yaml.safe_load(content)

    async def setup(self):
        """Initialize all components."""
        logger.info("Setting up bot...")

        # Data feed
        self.data_feed = LiveDataFeed(symbol=self.symbol)
        await self.data_feed.connect()

        # Strategy
        self.strategy = StrategyEvaluator(str(self.winner_path))

        # Risk manager
        initial_balance = self.config.get("initial_balance", 1000)
        self.risk_manager = RiskManager(
            initial_balance=initial_balance,
            risk_per_trade_pct=self.config.get("risk_per_trade_pct", 1.0),
            max_daily_loss_pct=self.config.get("max_daily_loss_pct", 3.0),
        )

        # Executor
        self.executor = OrderExecutor(
            api_key=os.getenv("BINANCE_API_KEY", ""),
            api_secret=os.getenv("BINANCE_API_SECRET", ""),
            symbol=self.symbol,
            paper_trading=self.paper_trading,
        )
        await self.executor.connect()

        # Monitor
        self.monitor = HealthMonitor()

        # Journal
        self.journal = TradeJournal()

        # Failure handler
        self.failure_handler = APIFailureHandler()

        logger.info("Bot setup complete")

    async def shutdown(self):
        """Cleanup resources."""
        logger.info("Shutting down...")

        self.running = False

        if self.executor:
            await self.executor.disconnect()

        if self.data_feed:
            await self.data_feed.disconnect()

        logger.info("Shutdown complete")

    async def main_loop(self, update_interval_sec: float = 60):
        """
        Main trading loop.

        Args:
            update_interval_sec: How often to check for signals
        """
        self.running = True
        last_daily_reset = datetime.utcnow()

        while self.running:
            try:
                await self.monitor.heartbeat()

                # Reset daily counters
                now = datetime.utcnow()
                if (now - last_daily_reset).days >= 1:
                    self.risk_manager.reset_daily()
                    self.journal.log_event("DAILY_RESET", "Daily P&L reset")
                    last_daily_reset = now

                # Update data
                await self.data_feed.update_all()

                # Check health
                health_ok = await self.monitor.check_health(
                    data_feed_connected=True,  # Would check real connectivity
                    executor_connected=True,
                )

                if not health_ok:
                    logger.warning("Health check failed, attempting reconnect...")
                    await self.monitor.exponential_backoff_retry()
                    await self.setup()
                    self.monitor.reset_retry()
                    continue

                # Get current data
                buffer = self.data_feed.get_buffer(self.timeframe)

                if len(buffer) < 2:
                    await asyncio.sleep(update_interval_sec)
                    continue

                # Check if new candle
                is_new = self.data_feed.is_new_candle(self.timeframe)

                if is_new:
                    await self._process_trading_signals(buffer)

                # Check open positions for TP/SL
                await self._check_exit_conditions(buffer)

                # Log status
                if is_new:
                    status = self.risk_manager.get_status()
                    logger.info(f"Status: {status}")

                await asyncio.sleep(update_interval_sec)

            except KeyboardInterrupt:
                logger.info("Keyboard interrupt received")
                break
            except Exception as e:
                logger.error(f"Main loop error: {e}", exc_info=True)
                self.failure_handler.record_failure(str(e))

                if self.failure_handler.should_halt():
                    logger.error("Too many failures, halting")
                    break

                await asyncio.sleep(update_interval_sec)

        await self.shutdown()

    async def _process_trading_signals(self, buffer):
        """Evaluate signals and process entries."""
        # Check if can open position
        if not self.risk_manager.can_open_position():
            return

        if self.current_position:
            return

        # Evaluate entry signal
        signal = self.strategy.evaluate_entry(buffer)

        if signal == 0:
            return

        # Risk management check
        risk_status = self.risk_manager.get_status()

        if risk_status["kill_switch"]:
            self.journal.log_event(
                "KILL_SWITCH",
                f"Trading halted: {risk_status['kill_switch_reason']}",
                "WARNING",
            )
            return

        # Get current price and ATR for exit levels
        current_price = buffer["close"].iloc[-1]
        atr = 100  # Placeholder - should calculate from indicators

        # Calculate position size
        direction = "long" if signal == 1 else "short"
        stop_loss = current_price - atr * 2 if direction == "long" else current_price + atr * 2
        take_profit = current_price + atr * 4 if direction == "long" else current_price - atr * 4

        size = self.risk_manager.calculate_position_size(
            current_price,
            stop_loss,
        )

        if size <= 0:
            logger.warning("Invalid position size")
            return

        # Place order
        order = await self.executor.place_order(
            direction=direction,
            quantity=size,
            entry_price=current_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
        )

        if order:
            self.current_position = (order.get("id", ""), direction)
            self.risk_manager.register_position()
            self.journal.log_event(
                "ENTRY",
                f"{direction.upper()} {size} @ {current_price}",
                "INFO",
            )

    async def _check_exit_conditions(self, buffer):
        """Check TP/SL and exit signals."""
        if not self.current_position:
            return

        order_id, direction = self.current_position
        current_price = buffer["close"].iloc[-1]

        # Check exit signal
        exit_signal = self.strategy.evaluate_exit(buffer, direction)

        orders = self.executor.get_open_orders()
        if order_id not in orders:
            self.current_position = None
            return

        order = orders[order_id]
        entry_price = order["entry_price"]
        stop_loss = order["stop_loss"]
        take_profit = order["take_profit"]

        # Check SL
        if direction == "long" and current_price <= stop_loss:
            await self._close_position(order_id, stop_loss, "SL")
        elif direction == "short" and current_price >= stop_loss:
            await self._close_position(order_id, stop_loss, "SL")

        # Check TP
        elif direction == "long" and current_price >= take_profit:
            await self._close_position(order_id, take_profit, "TP")
        elif direction == "short" and current_price <= take_profit:
            await self._close_position(order_id, take_profit, "TP")

        # Check exit signal
        elif exit_signal:
            await self._close_position(order_id, current_price, "SIGNAL")

    async def _close_position(self, order_id: str, exit_price: float, reason: str):
        """Close a position."""
        orders = self.executor.get_open_orders()
        if order_id not in orders:
            return

        order = orders[order_id]

        # Calculate P&L
        if order["direction"] == "long":
            pnl = (exit_price - order["entry_price"]) * order["quantity"]
        else:
            pnl = (order["entry_price"] - exit_price) * order["quantity"]

        # Close order
        await self.executor.close_order(order_id, exit_price, reason)

        # Update risk manager
        self.risk_manager.close_position(pnl)

        # Log trade
        self.journal.log_trade(
            order_id=order_id,
            direction=order["direction"],
            entry_time=order["time"],
            entry_price=order["entry_price"],
            entry_quantity=order["quantity"],
            exit_time=datetime.utcnow(),
            exit_price=exit_price,
            stop_loss=order["stop_loss"],
            take_profit=order["take_profit"],
            exit_reason=reason,
            pnl=pnl,
        )

        self.current_position = None

        # Show stats
        stats = self.journal.get_stats()
        logger.info(f"Journal stats: {stats}")


async def main():
    """Main entry point."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler("trading_bot.log"),
            logging.StreamHandler(),
        ],
    )

    bot = LiveTradingBot()

    try:
        await bot.setup()
        await bot.main_loop(update_interval_sec=60)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
    finally:
        await bot.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
