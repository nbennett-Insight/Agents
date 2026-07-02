"""Customer support resolution agent lab (mock MCP backend, no real DB).

Implements a training-friendly, deterministic agent for:
- returns
- billing disputes
- account issues

Tools are modeled after MCP tool contracts:
- get_customer
- lookup_order
- process_refund
- escalate_to_human
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
import re
from typing import Any, Dict, List, Optional, Tuple


TODAY = date(2026, 7, 2)


@dataclass
class ToolError(Exception):
    error_category: str  # transient | validation | permission | business
    is_retryable: bool
    description: str

    def to_payload(self) -> Dict[str, Any]:
        return {
            "ok": False,
            "errorCategory": self.error_category,
            "isRetryable": self.is_retryable,
            "description": self.description,
        }


@dataclass
class ToolCall:
    tool_name: str
    args: Dict[str, Any]


class MockSupportBackend:
    """In-memory backend used for lab-grade deterministic behavior."""

    def __init__(self) -> None:
        self.customers: Dict[str, Dict[str, Any]] = {
            "C1001": {
                "customer_id": "C1001",
                "name": "Alex Carter",
                "tier": "standard",
                "status": "active",
                "email_verified": True,
            },
            "C1002": {
                "customer_id": "C1002",
                "name": "Jordan Lee",
                "tier": "gold",
                "status": "active",
                "email_verified": True,
            },
            "C1003": {
                "customer_id": "C1003",
                "name": "Taylor Morgan",
                "tier": "standard",
                "status": "locked",
                "email_verified": True,
            },
            "C1004": {
                "customer_id": "C1004",
                "name": "Casey Nguyen",
                "tier": "standard",
                "status": "active",
                "email_verified": False,
            },
        }

        self.orders: Dict[str, Dict[str, Any]] = {
            "O5001": {
                "order_id": "O5001",
                "customer_id": "C1001",
                "status": "delivered",
                "delivered_date": "2026-06-20",
                "amount": 89.99,
                "currency": "USD",
                "billing_dispute": 0.0,
                "refundable": True,
            },
            "O5002": {
                "order_id": "O5002",
                "customer_id": "C1001",
                "status": "delivered",
                "delivered_date": "2026-05-01",
                "amount": 120.0,
                "currency": "USD",
                "billing_dispute": 0.0,
                "refundable": False,
            },
            "O5003": {
                "order_id": "O5003",
                "customer_id": "C1002",
                "status": "delivered",
                "delivered_date": "2026-06-29",
                "amount": 399.0,
                "currency": "USD",
                "billing_dispute": 20.0,
                "refundable": True,
            },
            "O5004": {
                "order_id": "O5004",
                "customer_id": "C1002",
                "status": "delivered",
                "delivered_date": "2026-06-10",
                "amount": 1499.0,
                "currency": "USD",
                "billing_dispute": 250.0,
                "refundable": True,
            },
            "O5005": {
                "order_id": "O5005",
                "customer_id": "C1004",
                "status": "in_transit",
                "delivered_date": None,
                "amount": 59.0,
                "currency": "USD",
                "billing_dispute": 0.0,
                "refundable": False,
            },
        }

        self.refunds: List[Dict[str, Any]] = []
        self.escalations: List[Dict[str, Any]] = []

    # MCP tool: get_customer
    def get_customer(self, customer_id: str) -> Dict[str, Any]:
        customer = self.customers.get(customer_id)
        if customer is None:
            raise ToolError(
                error_category="validation",
                is_retryable=False,
                description=f"Customer '{customer_id}' not found.",
            )
        return customer

    # MCP tool: lookup_order
    def lookup_order(self, order_id: str) -> Dict[str, Any]:
        order = self.orders.get(order_id)
        if order is None:
            raise ToolError(
                error_category="validation",
                is_retryable=False,
                description=f"Order '{order_id}' not found.",
            )
        return order

    # MCP tool: process_refund
    def process_refund(
        self,
        order_id: str,
        amount: float,
        reason: str,
        actor_role: str,
    ) -> Dict[str, Any]:
        if actor_role not in {"agent", "manager"}:
            raise ToolError(
                error_category="permission",
                is_retryable=False,
                description="actor_role must be one of: agent, manager.",
            )

        order = self.orders.get(order_id)
        if order is None:
            raise ToolError(
                error_category="validation",
                is_retryable=False,
                description=f"Order '{order_id}' not found for refund.",
            )

        if amount <= 0:
            raise ToolError(
                error_category="validation",
                is_retryable=False,
                description="Refund amount must be greater than zero.",
            )

        if actor_role == "agent" and amount > 200.0:
            raise ToolError(
                error_category="permission",
                is_retryable=False,
                description="Agents may not approve refunds above 200 USD.",
            )

        refund = {
            "refund_id": f"R{len(self.refunds) + 1:05d}",
            "order_id": order_id,
            "amount": round(amount, 2),
            "reason": reason,
            "status": "approved",
        }
        self.refunds.append(refund)
        return refund

    # MCP tool: escalate_to_human
    def escalate_to_human(
        self,
        customer_id: str,
        reason: str,
        priority: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        if priority not in {"low", "medium", "high"}:
            raise ToolError(
                error_category="validation",
                is_retryable=False,
                description="priority must be one of low, medium, high.",
            )
        ticket = {
            "ticket_id": f"H{len(self.escalations) + 1:05d}",
            "customer_id": customer_id,
            "reason": reason,
            "priority": priority,
            "context": context or {},
            "status": "open",
        }
        self.escalations.append(ticket)
        return ticket


class SupportResolutionAgent:
    """A deterministic orchestration layer for lab training and evaluation."""

    def __init__(
        self,
        return_window_days: int = 30,
        auto_refund_limit: float = 100.0,
        max_retries: int = 1,
    ) -> None:
        self.return_window_days = return_window_days
        self.auto_refund_limit = auto_refund_limit
        self.max_retries = max_retries

        self.backend = MockSupportBackend()
        self.tool_impls = {
            "get_customer": self.backend.get_customer,
            "lookup_order": self.backend.lookup_order,
            "process_refund": self.backend.process_refund,
            "escalate_to_human": self.backend.escalate_to_human,
        }

    def _execute_tool(self, call: ToolCall) -> Dict[str, Any]:
        impl = self.tool_impls.get(call.tool_name)
        if impl is None:
            return {
                "ok": False,
                "errorCategory": "validation",
                "isRetryable": False,
                "description": f"Unknown tool '{call.tool_name}'.",
            }

        retries = 0
        while True:
            try:
                data = impl(**call.args)
                return {"ok": True, "tool": call.tool_name, "data": data}
            except ToolError as err:
                if err.error_category == "transient" and err.is_retryable and retries < self.max_retries:
                    retries += 1
                    continue
                return err.to_payload()
            except Exception as err:
                return {
                    "ok": False,
                    "errorCategory": "transient",
                    "isRetryable": False,
                    "description": f"Unhandled tool exception: {err}",
                }

    @staticmethod
    def _extract_id(text: str, prefix: str) -> Optional[str]:
        pattern = rf"\b{prefix}[0-9]{{4,6}}\b"
        match = re.search(pattern, text.upper())
        return match.group(0) if match else None

    @staticmethod
    def _days_since(date_string: str) -> int:
        dt = datetime.strptime(date_string, "%Y-%m-%d").date()
        return (TODAY - dt).days

    def _resolve_return(self, customer_id: str, order_id: str, actor_role: str) -> Dict[str, Any]:
        cust = self._execute_tool(ToolCall("get_customer", {"customer_id": customer_id}))
        if not cust.get("ok"):
            return self._build_response("escalated", [cust], "Could not verify customer; escalated.")

        order = self._execute_tool(ToolCall("lookup_order", {"order_id": order_id}))
        if not order.get("ok"):
            return self._build_response("escalated", [cust, order], "Order lookup failed; escalated.")

        order_data = order["data"]
        if order_data["customer_id"] != customer_id:
            esc = self._execute_tool(
                ToolCall(
                    "escalate_to_human",
                    {
                        "customer_id": customer_id,
                        "reason": "Order does not belong to customer",
                        "priority": "high",
                        "context": {"order_id": order_id},
                    },
                )
            )
            return self._build_response(
                "escalated",
                [cust, order, esc],
                "Order ownership mismatch, escalated for fraud review.",
            )

        if order_data["status"] != "delivered" or not order_data["delivered_date"]:
            esc = self._execute_tool(
                ToolCall(
                    "escalate_to_human",
                    {
                        "customer_id": customer_id,
                        "reason": "Return requested before delivery",
                        "priority": "medium",
                        "context": {"order_id": order_id},
                    },
                )
            )
            return self._build_response(
                "escalated",
                [cust, order, esc],
                "Order is not delivered yet; escalated for manual exception handling.",
            )

        age_days = self._days_since(order_data["delivered_date"])
        if age_days > self.return_window_days:
            esc = self._execute_tool(
                ToolCall(
                    "escalate_to_human",
                    {
                        "customer_id": customer_id,
                        "reason": "Return window expired",
                        "priority": "medium",
                        "context": {"order_id": order_id, "age_days": age_days},
                    },
                )
            )
            return self._build_response(
                "escalated",
                [cust, order, esc],
                "Return window is expired, escalated for policy override review.",
            )

        amount = float(order_data["amount"])
        refund = self._execute_tool(
            ToolCall(
                "process_refund",
                {
                    "order_id": order_id,
                    "amount": amount,
                    "reason": "Approved return within policy window",
                    "actor_role": actor_role,
                },
            )
        )

        if refund.get("ok"):
            return self._build_response(
                "resolved",
                [cust, order, refund],
                f"Return approved and refund {refund['data']['refund_id']} created.",
            )

        esc = self._execute_tool(
            ToolCall(
                "escalate_to_human",
                {
                    "customer_id": customer_id,
                    "reason": "Refund blocked by role/policy",
                    "priority": "high",
                    "context": {"order_id": order_id, "refund_error": refund},
                },
            )
        )
        return self._build_response(
            "escalated",
            [cust, order, refund, esc],
            "Return eligible but refund authorization blocked; escalated.",
        )

    def _resolve_billing_dispute(self, customer_id: str, order_id: str, actor_role: str) -> Dict[str, Any]:
        cust = self._execute_tool(ToolCall("get_customer", {"customer_id": customer_id}))
        order = self._execute_tool(ToolCall("lookup_order", {"order_id": order_id}))
        if not cust.get("ok") or not order.get("ok"):
            return self._build_response("escalated", [cust, order], "Unable to validate billing context; escalated.")

        order_data = order["data"]
        dispute = float(order_data.get("billing_dispute", 0.0))
        if dispute <= 0:
            return self._build_response(
                "resolved",
                [cust, order],
                "No billing discrepancy found on this order.",
            )

        if dispute <= self.auto_refund_limit:
            refund = self._execute_tool(
                ToolCall(
                    "process_refund",
                    {
                        "order_id": order_id,
                        "amount": dispute,
                        "reason": "Billing dispute auto-resolution",
                        "actor_role": actor_role,
                    },
                )
            )
            if refund.get("ok"):
                return self._build_response(
                    "resolved",
                    [cust, order, refund],
                    f"Billing issue resolved with refund {refund['data']['refund_id']} for {dispute:.2f}.",
                )

        esc = self._execute_tool(
            ToolCall(
                "escalate_to_human",
                {
                    "customer_id": customer_id,
                    "reason": "Large or blocked billing dispute",
                    "priority": "high",
                    "context": {"order_id": order_id, "dispute": dispute},
                },
            )
        )
        return self._build_response(
            "escalated",
            [cust, order, esc],
            "Billing dispute requires manual investigation; escalated.",
        )

    def _resolve_account_issue(self, customer_id: str) -> Dict[str, Any]:
        cust = self._execute_tool(ToolCall("get_customer", {"customer_id": customer_id}))
        if not cust.get("ok"):
            return self._build_response("escalated", [cust], "Account not found; escalated.")

        customer = cust["data"]
        if customer["status"] == "locked":
            esc = self._execute_tool(
                ToolCall(
                    "escalate_to_human",
                    {
                        "customer_id": customer_id,
                        "reason": "Account lockout requires identity verification",
                        "priority": "high",
                        "context": {"status": customer["status"]},
                    },
                )
            )
            return self._build_response(
                "escalated",
                [cust, esc],
                "Account is locked and needs specialist verification.",
            )

        if not customer["email_verified"]:
            esc = self._execute_tool(
                ToolCall(
                    "escalate_to_human",
                    {
                        "customer_id": customer_id,
                        "reason": "Unverified email blocks self-service recovery",
                        "priority": "medium",
                        "context": {"email_verified": False},
                    },
                )
            )
            return self._build_response(
                "escalated",
                [cust, esc],
                "Account exists but email is unverified; escalated for secure verification.",
            )

        return self._build_response(
            "resolved",
            [cust],
            "Account is active. Guided customer through self-service reset path.",
        )

    @staticmethod
    def _build_response(outcome: str, tool_results: List[Dict[str, Any]], message: str) -> Dict[str, Any]:
        return {
            "outcome": outcome,  # resolved | escalated
            "message": message,
            "tool_results": tool_results,
            "first_contact_resolved": outcome == "resolved",
        }

    def handle_request(self, user_message: str, actor_role: str = "agent") -> Dict[str, Any]:
        text = user_message.lower()
        customer_id = self._extract_id(user_message, "C")
        order_id = self._extract_id(user_message, "O")

        if "return" in text:
            if not customer_id or not order_id:
                return self._build_response(
                    "escalated",
                    [],
                    "Missing customer/order identifiers for return request; escalated.",
                )
            return self._resolve_return(customer_id, order_id, actor_role)

        if "billing" in text or "charged" in text or "invoice" in text:
            if not customer_id or not order_id:
                return self._build_response(
                    "escalated",
                    [],
                    "Missing customer/order identifiers for billing dispute; escalated.",
                )
            return self._resolve_billing_dispute(customer_id, order_id, actor_role)

        if "account" in text or "locked" in text or "login" in text:
            if not customer_id:
                return self._build_response(
                    "escalated",
                    [],
                    "Missing customer identifier for account issue; escalated.",
                )
            return self._resolve_account_issue(customer_id)

        if customer_id:
            esc = self._execute_tool(
                ToolCall(
                    "escalate_to_human",
                    {
                        "customer_id": customer_id,
                        "reason": "High ambiguity request outside supported domains",
                        "priority": "medium",
                        "context": {"message": user_message},
                    },
                )
            )
            return self._build_response("escalated", [esc], "Request is too ambiguous; escalated to human.")

        return self._build_response("escalated", [], "Unable to identify customer context; escalated.")


def demo() -> None:
    agent = SupportResolutionAgent(return_window_days=30, auto_refund_limit=100.0)

    samples = [
        "I want to return order O5001 for customer C1001",
        "Billing dispute: customer C1002 says order O5003 was overcharged",
        "My account is locked for customer C1003",
        "Need help with something weird, customer C1001",
    ]

    for msg in samples:
        print("=" * 80)
        print(f"USER: {msg}")
        out = agent.handle_request(msg, actor_role="agent")
        print(f"OUTCOME: {out['outcome']}")
        print(f"MESSAGE: {out['message']}")


if __name__ == "__main__":
    demo()
