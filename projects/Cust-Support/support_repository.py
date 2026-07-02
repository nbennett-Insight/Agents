"""SQLite-backed mock repository for the support agent lab."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional


class SQLiteSupportRepository:
    def __init__(self, db_path: str = "support_mock.db", reset: bool = False) -> None:
        self.db_path = str(Path(db_path))
        if reset and Path(self.db_path).exists():
            Path(self.db_path).unlink()

        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self._create_schema()
        self.seed_defaults()

    def _create_schema(self) -> None:
        cur = self.conn.cursor()
        cur.executescript(
            """
            CREATE TABLE IF NOT EXISTS customers (
                customer_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                tier TEXT NOT NULL,
                status TEXT NOT NULL,
                email_verified INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS orders (
                order_id TEXT PRIMARY KEY,
                customer_id TEXT NOT NULL,
                status TEXT NOT NULL,
                delivered_date TEXT,
                amount REAL NOT NULL,
                currency TEXT NOT NULL,
                billing_dispute REAL NOT NULL,
                refundable INTEGER NOT NULL,
                FOREIGN KEY(customer_id) REFERENCES customers(customer_id)
            );

            CREATE TABLE IF NOT EXISTS refunds (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                refund_id TEXT UNIQUE NOT NULL,
                order_id TEXT NOT NULL,
                amount REAL NOT NULL,
                reason TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(order_id) REFERENCES orders(order_id)
            );

            CREATE TABLE IF NOT EXISTS escalations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_id TEXT UNIQUE NOT NULL,
                customer_id TEXT NOT NULL,
                reason TEXT NOT NULL,
                priority TEXT NOT NULL,
                context_json TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(customer_id) REFERENCES customers(customer_id)
            );

            CREATE TABLE IF NOT EXISTS tool_call_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tool_name TEXT NOT NULL,
                args_json TEXT NOT NULL,
                ok INTEGER NOT NULL,
                error_category TEXT,
                error_description TEXT,
                forced_failure INTEGER NOT NULL,
                latency_ms INTEGER NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        self.conn.commit()

    def seed_defaults(self) -> None:
        if self._count("customers") > 0:
            return

        customers = [
            ("C1001", "Alex Carter", "standard", "active", 1),
            ("C1002", "Jordan Lee", "gold", "active", 1),
            ("C1003", "Taylor Morgan", "standard", "locked", 1),
            ("C1004", "Casey Nguyen", "standard", "active", 0),
        ]
        orders = [
            ("O5001", "C1001", "delivered", "2026-06-20", 89.99, "USD", 0.0, 1),
            ("O5002", "C1001", "delivered", "2026-05-01", 120.0, "USD", 0.0, 0),
            ("O5003", "C1002", "delivered", "2026-06-29", 399.0, "USD", 20.0, 1),
            ("O5004", "C1002", "delivered", "2026-06-10", 1499.0, "USD", 250.0, 1),
            ("O5005", "C1004", "in_transit", None, 59.0, "USD", 0.0, 0),
        ]

        cur = self.conn.cursor()
        cur.executemany(
            "INSERT INTO customers(customer_id, name, tier, status, email_verified) VALUES (?, ?, ?, ?, ?)",
            customers,
        )
        cur.executemany(
            """
            INSERT INTO orders(
                order_id, customer_id, status, delivered_date, amount, currency, billing_dispute, refundable
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            orders,
        )
        self.conn.commit()

    def _count(self, table_name: str) -> int:
        cur = self.conn.cursor()
        cur.execute(f"SELECT COUNT(*) as c FROM {table_name}")
        return int(cur.fetchone()["c"])

    def get_customer(self, customer_id: str) -> Optional[Dict[str, Any]]:
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM customers WHERE customer_id = ?", (customer_id,))
        row = cur.fetchone()
        if row is None:
            return None
        return {
            "customer_id": row["customer_id"],
            "name": row["name"],
            "tier": row["tier"],
            "status": row["status"],
            "email_verified": bool(row["email_verified"]),
        }

    def get_order(self, order_id: str) -> Optional[Dict[str, Any]]:
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM orders WHERE order_id = ?", (order_id,))
        row = cur.fetchone()
        if row is None:
            return None
        return {
            "order_id": row["order_id"],
            "customer_id": row["customer_id"],
            "status": row["status"],
            "delivered_date": row["delivered_date"],
            "amount": float(row["amount"]),
            "currency": row["currency"],
            "billing_dispute": float(row["billing_dispute"]),
            "refundable": bool(row["refundable"]),
        }

    def find_refund(self, order_id: str, amount: float, reason: str) -> Optional[Dict[str, Any]]:
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT * FROM refunds
            WHERE order_id = ? AND amount = ? AND reason = ?
            ORDER BY id DESC LIMIT 1
            """,
            (order_id, round(float(amount), 2), reason),
        )
        row = cur.fetchone()
        if row is None:
            return None
        return {
            "refund_id": row["refund_id"],
            "order_id": row["order_id"],
            "amount": float(row["amount"]),
            "reason": row["reason"],
            "status": row["status"],
            "idempotent": True,
        }

    def create_refund(self, order_id: str, amount: float, reason: str, status: str = "approved") -> Dict[str, Any]:
        cur = self.conn.cursor()
        cur.execute("SELECT COUNT(*) as c FROM refunds")
        next_id = int(cur.fetchone()["c"]) + 1
        refund_id = f"R{next_id:05d}"

        cur.execute(
            "INSERT INTO refunds(refund_id, order_id, amount, reason, status) VALUES (?, ?, ?, ?, ?)",
            (refund_id, order_id, round(float(amount), 2), reason, status),
        )
        self.conn.commit()
        return {
            "refund_id": refund_id,
            "order_id": order_id,
            "amount": round(float(amount), 2),
            "reason": reason,
            "status": status,
        }

    def create_escalation(
        self,
        customer_id: str,
        reason: str,
        priority: str,
        context: Optional[Dict[str, Any]] = None,
        status: str = "open",
    ) -> Dict[str, Any]:
        cur = self.conn.cursor()
        cur.execute("SELECT COUNT(*) as c FROM escalations")
        next_id = int(cur.fetchone()["c"]) + 1
        ticket_id = f"H{next_id:05d}"

        context_json = json.dumps(context or {}, sort_keys=True)
        cur.execute(
            """
            INSERT INTO escalations(ticket_id, customer_id, reason, priority, context_json, status)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (ticket_id, customer_id, reason, priority, context_json, status),
        )
        self.conn.commit()

        return {
            "ticket_id": ticket_id,
            "customer_id": customer_id,
            "reason": reason,
            "priority": priority,
            "context": context or {},
            "status": status,
        }

    def log_tool_call(
        self,
        tool_name: str,
        args: Dict[str, Any],
        ok: bool,
        error_category: Optional[str],
        error_description: Optional[str],
        forced_failure: bool,
        latency_ms: int,
    ) -> None:
        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT INTO tool_call_logs(
                tool_name, args_json, ok, error_category, error_description, forced_failure, latency_ms
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                tool_name,
                json.dumps(args, sort_keys=True),
                1 if ok else 0,
                error_category,
                error_description,
                1 if forced_failure else 0,
                latency_ms,
            ),
        )
        self.conn.commit()

    def recent_tool_logs(self, limit: int = 20) -> List[Dict[str, Any]]:
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT id, tool_name, args_json, ok, error_category, error_description, forced_failure, latency_ms, created_at
            FROM tool_call_logs
            ORDER BY id DESC
            LIMIT ?
            """,
            (int(limit),),
        )
        rows = cur.fetchall()
        result: List[Dict[str, Any]] = []
        for row in rows:
            result.append(
                {
                    "id": row["id"],
                    "tool_name": row["tool_name"],
                    "args": json.loads(row["args_json"]),
                    "ok": bool(row["ok"]),
                    "error_category": row["error_category"],
                    "error_description": row["error_description"],
                    "forced_failure": bool(row["forced_failure"]),
                    "latency_ms": int(row["latency_ms"]),
                    "created_at": row["created_at"],
                }
            )
        return result

    def close(self) -> None:
        self.conn.close()
