"""
Stage 4e: Trade Journal
Log all trades to SQLite and CSV for analysis.
"""

import sqlite3
import csv
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class TradeJournal:
    """Record all trades and events."""

    def __init__(self, db_path: Path = None):
        """
        Initialize journal.

        Args:
            db_path: Path to SQLite database
        """
        self.db_path = db_path or Path("trade_journal.db")
        self.csv_path = self.db_path.parent / "trades.csv"

        self._init_db()

    def _init_db(self):
        """Initialize SQLite database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id TEXT UNIQUE,
                direction TEXT,
                entry_time TIMESTAMP,
                entry_price REAL,
                entry_quantity REAL,
                exit_time TIMESTAMP,
                exit_price REAL,
                stop_loss REAL,
                take_profit REAL,
                exit_reason TEXT,
                pnl REAL,
                pnl_pct REAL,
                commission REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT,
                message TEXT,
                severity TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()
        conn.close()

        logger.info(f"Journal initialized: {self.db_path}")

    def log_trade(
        self,
        order_id: str,
        direction: str,
        entry_time: datetime,
        entry_price: float,
        entry_quantity: float,
        exit_time: datetime,
        exit_price: float,
        stop_loss: float,
        take_profit: float,
        exit_reason: str,
        pnl: float,
        commission: float = 0.0,
    ):
        """Log a completed trade."""
        pnl_pct = (pnl / (entry_price * entry_quantity)) * 100 if entry_price * entry_quantity > 0 else 0

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO trades (
                    order_id, direction, entry_time, entry_price, entry_quantity,
                    exit_time, exit_price, stop_loss, take_profit, exit_reason,
                    pnl, pnl_pct, commission
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                order_id,
                direction,
                entry_time,
                entry_price,
                entry_quantity,
                exit_time,
                exit_price,
                stop_loss,
                take_profit,
                exit_reason,
                pnl,
                pnl_pct,
                commission,
            ))

            conn.commit()
            conn.close()

            logger.info(
                f"Trade logged: {direction} {entry_quantity} @ {entry_price} -> "
                f"{exit_price} | PnL: {pnl:.2f} ({pnl_pct:.2f}%) | {exit_reason}"
            )

            # Also write to CSV
            self._append_to_csv({
                "order_id": order_id,
                "direction": direction,
                "entry_time": entry_time.isoformat(),
                "entry_price": entry_price,
                "entry_quantity": entry_quantity,
                "exit_time": exit_time.isoformat(),
                "exit_price": exit_price,
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "exit_reason": exit_reason,
                "pnl": pnl,
                "pnl_pct": pnl_pct,
                "commission": commission,
            })

        except sqlite3.IntegrityError:
            logger.warning(f"Duplicate trade ID: {order_id}")
        except Exception as e:
            logger.error(f"Failed to log trade: {e}")

    def log_event(self, event_type: str, message: str, severity: str = "INFO"):
        """Log a system event."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO events (event_type, message, severity)
                VALUES (?, ?, ?)
            """, (event_type, message, severity))

            conn.commit()
            conn.close()

            if severity == "ERROR":
                logger.error(f"[{event_type}] {message}")
            elif severity == "WARNING":
                logger.warning(f"[{event_type}] {message}")
            else:
                logger.info(f"[{event_type}] {message}")

        except Exception as e:
            logger.error(f"Failed to log event: {e}")

    def _append_to_csv(self, trade_dict: Dict):
        """Append trade to CSV file."""
        try:
            csv_exists = self.csv_path.exists()

            with open(self.csv_path, "a", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=trade_dict.keys())

                if not csv_exists:
                    writer.writeheader()

                writer.writerow(trade_dict)

        except Exception as e:
            logger.error(f"Failed to write CSV: {e}")

    def get_trades(self, limit: int = 100) -> List[Dict]:
        """Get recent trades from database."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row

            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM trades
                ORDER BY created_at DESC
                LIMIT ?
            """, (limit,))

            trades = [dict(row) for row in cursor.fetchall()]
            conn.close()

            return trades

        except Exception as e:
            logger.error(f"Failed to fetch trades: {e}")
            return []

    def get_stats(self) -> Dict:
        """Calculate trading statistics."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) as total FROM trades")
            total_trades = cursor.fetchone()[0]

            cursor.execute("SELECT SUM(pnl) as total_pnl FROM trades")
            total_pnl = cursor.fetchone()[0] or 0

            cursor.execute("SELECT COUNT(*) as wins FROM trades WHERE pnl > 0")
            winning_trades = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) as losses FROM trades WHERE pnl <= 0")
            losing_trades = cursor.fetchone()[0]

            cursor.execute("SELECT AVG(pnl_pct) as avg_pnl_pct FROM trades")
            avg_return = cursor.fetchone()[0] or 0

            conn.close()

            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0

            return {
                "total_trades": total_trades,
                "winning_trades": winning_trades,
                "losing_trades": losing_trades,
                "win_rate_%": win_rate,
                "total_pnl": total_pnl,
                "avg_return_%": avg_return,
            }

        except Exception as e:
            logger.error(f"Failed to calculate stats: {e}")
            return {}
