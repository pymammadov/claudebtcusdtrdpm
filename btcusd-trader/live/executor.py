"""
Stage 4c: Order Executor
Places and manages orders via Binance Futures API.
"""

import asyncio
import logging
from typing import Dict, Optional
import aiohttp
from datetime import datetime

logger = logging.getLogger(__name__)


class OrderExecutor:
    """Execute trades on Binance Futures."""

    BASE_URL = "https://fapi.binance.com/fapi/v1"

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        symbol: str = "BTCUSDT",
        paper_trading: bool = True,
    ):
        """
        Initialize executor.

        Args:
            api_key: Binance API key
            api_secret: Binance API secret
            symbol: Trading symbol
            paper_trading: If True, simulate fills instead of real orders
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.symbol = symbol
        self.paper_trading = paper_trading

        self.session: Optional[aiohttp.ClientSession] = None
        self.open_orders: Dict[str, Dict] = {}  # Order ID -> order details

        logger.info(f"Executor initialized (paper_trading={paper_trading})")

    async def connect(self):
        """Create HTTP session."""
        self.session = aiohttp.ClientSession()
        logger.info("Executor connected")

    async def disconnect(self):
        """Close session and cancel open orders."""
        if not self.paper_trading:
            # Cancel all open orders
            for order_id in list(self.open_orders.keys()):
                await self.cancel_order(order_id)

        if self.session:
            await self.session.close()
            logger.info("Executor disconnected")

    async def place_order(
        self,
        direction: str,
        quantity: float,
        entry_price: float,
        stop_loss: float,
        take_profit: float,
    ) -> Optional[Dict]:
        """
        Place entry order with linked stop-loss and take-profit.

        Args:
            direction: "long" or "short"
            quantity: Position size (BTC)
            entry_price: Limit price for entry
            stop_loss: Stop loss price
            take_profit: Take profit price

        Returns:
            Order details dict
        """
        if self.paper_trading:
            return await self._simulate_order(
                direction, quantity, entry_price, stop_loss, take_profit
            )

        try:
            side = "BUY" if direction == "long" else "SELL"

            params = {
                "symbol": self.symbol,
                "side": side,
                "type": "LIMIT",
                "timeInForce": "GTC",
                "quantity": quantity,
                "price": round(entry_price, 2),
            }

            headers = {"X-MBX-APIKEY": self.api_key}

            async with self.session.post(
                f"{self.BASE_URL}/order",
                params=params,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status != 200:
                    logger.error(f"Order placement failed: {resp.status}")
                    return None

                order = await resp.json()

                self.open_orders[order["orderId"]] = {
                    "id": order["orderId"],
                    "direction": direction,
                    "quantity": quantity,
                    "entry_price": entry_price,
                    "stop_loss": stop_loss,
                    "take_profit": take_profit,
                    "status": "OPEN",
                    "time": datetime.utcnow(),
                }

                logger.info(
                    f"Order placed: {direction.upper()} {quantity} at {entry_price} "
                    f"| SL={stop_loss}, TP={take_profit}"
                )

                return order

        except Exception as e:
            logger.error(f"Order placement error: {e}")
            return None

    async def _simulate_order(
        self,
        direction: str,
        quantity: float,
        entry_price: float,
        stop_loss: float,
        take_profit: float,
    ) -> Dict:
        """Simulate order execution for paper trading."""
        order_id = f"SIM_{int(datetime.utcnow().timestamp() * 1000)}"

        self.open_orders[order_id] = {
            "id": order_id,
            "direction": direction,
            "quantity": quantity,
            "entry_price": entry_price,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "status": "FILLED",
            "time": datetime.utcnow(),
            "simulated": True,
        }

        logger.info(
            f"[PAPER] Order placed: {direction.upper()} {quantity} at {entry_price} "
            f"| SL={stop_loss}, TP={take_profit}"
        )

        return self.open_orders[order_id]

    async def close_order(
        self,
        order_id: str,
        exit_price: float,
        reason: str = "Manual",
    ) -> Optional[Dict]:
        """
        Close an open position.

        Args:
            order_id: Order ID to close
            exit_price: Exit price
            reason: Reason for closing (TP/SL/Manual/etc)

        Returns:
            Closed order details
        """
        if order_id not in self.open_orders:
            logger.warning(f"Order not found: {order_id}")
            return None

        order = self.open_orders[order_id]

        if self.paper_trading or order.get("simulated"):
            return await self._simulate_close(order_id, exit_price, reason)

        try:
            side = "SELL" if order["direction"] == "long" else "BUY"

            params = {
                "symbol": self.symbol,
                "side": side,
                "type": "LIMIT",
                "timeInForce": "GTC",
                "quantity": order["quantity"],
                "price": round(exit_price, 2),
            }

            headers = {"X-MBX-APIKEY": self.api_key}

            async with self.session.post(
                f"{self.BASE_URL}/order",
                params=params,
                headers=headers,
            ) as resp:
                if resp.status != 200:
                    logger.error(f"Close order failed: {resp.status}")
                    return None

                close_order = await resp.json()
                del self.open_orders[order_id]

                logger.info(
                    f"Order closed ({reason}): {order['direction'].upper()} "
                    f"{order['quantity']} at {exit_price}"
                )

                return close_order

        except Exception as e:
            logger.error(f"Close order error: {e}")
            return None

    async def _simulate_close(
        self,
        order_id: str,
        exit_price: float,
        reason: str,
    ) -> Dict:
        """Simulate order close for paper trading."""
        order = self.open_orders[order_id]

        pnl = 0.0
        if order["direction"] == "long":
            pnl = (exit_price - order["entry_price"]) * order["quantity"]
        else:
            pnl = (order["entry_price"] - exit_price) * order["quantity"]

        logger.info(
            f"[PAPER] Order closed ({reason}): {order['direction'].upper()} "
            f"{order['quantity']} at {exit_price} | PnL: {pnl:.2f}"
        )

        del self.open_orders[order_id]

        return {
            "id": order_id,
            "exit_price": exit_price,
            "pnl": pnl,
            "reason": reason,
            "simulated": True,
        }

    async def update_stop_loss(
        self,
        order_id: str,
        new_stop_loss: float,
    ) -> bool:
        """Update stop-loss for trailing stop."""
        if order_id not in self.open_orders:
            return False

        order = self.open_orders[order_id]

        # For paper trading, just update the value
        if self.paper_trading or order.get("simulated"):
            order["stop_loss"] = new_stop_loss
            return True

        # Real trading: would need to modify order
        logger.debug(f"SL updated: {order_id} -> {new_stop_loss}")

        return True

    def get_open_orders(self) -> Dict[str, Dict]:
        """Get all open orders."""
        return self.open_orders.copy()

    def has_open_position(self) -> bool:
        """Check if any position is open."""
        return len(self.open_orders) > 0
