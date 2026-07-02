"""Support agent runtime that calls tools through an MCP-like protocol layer."""

from __future__ import annotations

from datetime import date, datetime
import re
from typing import Any, Callable, Dict, List, Optional, Tuple

from mcp_mock_layer import MCPMockServer, ToolError, ToolSpec
from support_repository import SQLiteSupportRepository


TODAY = date(2026, 7, 2)


class SupportMCPAgent:
    def __init__(
        self,
        mcp_server: MCPMockServer,
        return_window_days: int = 30,
        auto_refund_limit: float = 100.0,
        max_retries: int = 1,
        verbose: bool = False,
        trace_sink: Optional[Callable[[str], None]] = None,
    ) -> None:
        self.server = mcp_server
        self.return_window_days = return_window_days
        self.auto_refund_limit = auto_refund_limit
        self.max_retries = max_retries
        self.verbose = verbose
        self._trace_sink = trace_sink

    def set_verbose(self, verbose: bool) -> None:
        self.verbose = verbose

    def _trace(self, message: str) -> None:
        if self.verbose and self._trace_sink is not None:
            self._trace_sink(message)

    def _mcp_call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        request = {
            "jsonrpc": "2.0",
            "id": f"call-{name}",
            "method": "tools/call",
            "params": {"name": name, "arguments": arguments},
        }
        self._trace(f"MCP request -> tools/call {name} {arguments}")
        response = self.server.handle_mcp_request(request)

        if "error" in response:
            payload = {
                "ok": False,
                "errorCategory": "transient",
                "isRetryable": False,
                "description": f"MCP transport error: {response['error']}",
            }
            self._trace(f"MCP response <- ERROR {payload}")
            return payload

        result = response.get("result", {})
        self._trace(f"MCP response <- {result}")
        return result

    def _execute_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        attempts = 0
        while True:
            out = self._mcp_call_tool(name, arguments)
            if out.get("ok"):
                return out
            if out.get("errorCategory") == "transient" and out.get("isRetryable") and attempts < self.max_retries:
                attempts += 1
                self._trace(f"Retrying tool {name}, attempt {attempts}")
                continue
            return out

    @staticmethod
    def _extract_id(text: str, prefix: str) -> Optional[str]:
        pattern = rf"\b{prefix}[0-9]{{4,6}}\b"
        match = re.search(pattern, text.upper())
        return match.group(0) if match else None

    @staticmethod
    def _days_since(date_string: str) -> int:
        dt = datetime.strptime(date_string, "%Y-%m-%d").date()
        return (TODAY - dt).days

    @staticmethod
    def _build_response(outcome: str, message: str, tool_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        return {
            "outcome": outcome,
            "message": message,
            "tool_results": tool_results,
            "first_contact_resolved": outcome == "resolved",
        }

    def _resolve_return(self, customer_id: str, order_id: str, actor_role: str) -> Dict[str, Any]:
        tool_results: List[Dict[str, Any]] = []

        cust = self._execute_tool("get_customer", {"customer_id": customer_id})
        tool_results.append(cust)
        if not cust.get("ok"):
            return self._build_response("escalated", "Could not verify customer; escalated.", tool_results)

        order = self._execute_tool("lookup_order", {"order_id": order_id})
        tool_results.append(order)
        if not order.get("ok"):
            return self._build_response("escalated", "Order lookup failed; escalated.", tool_results)

        order_data = order["data"]

        if order_data["customer_id"] != customer_id:
            esc = self._execute_tool(
                "escalate_to_human",
                {
                    "customer_id": customer_id,
                    "reason": "Order does not belong to customer",
                    "priority": "high",
                    "context": {"order_id": order_id},
                },
            )
            tool_results.append(esc)
            return self._build_response(
                "escalated",
                "Order ownership mismatch, escalated for fraud review.",
                tool_results,
            )

        if order_data["status"] != "delivered" or not order_data["delivered_date"]:
            esc = self._execute_tool(
                "escalate_to_human",
                {
                    "customer_id": customer_id,
                    "reason": "Return requested before delivery",
                    "priority": "medium",
                    "context": {"order_id": order_id},
                },
            )
            tool_results.append(esc)
            return self._build_response(
                "escalated",
                "Order is not delivered yet; escalated for manual exception handling.",
                tool_results,
            )

        age_days = self._days_since(order_data["delivered_date"])
        if age_days > self.return_window_days:
            esc = self._execute_tool(
                "escalate_to_human",
                {
                    "customer_id": customer_id,
                    "reason": "Return window expired",
                    "priority": "medium",
                    "context": {"order_id": order_id, "age_days": age_days},
                },
            )
            tool_results.append(esc)
            return self._build_response(
                "escalated",
                "Return window is expired, escalated for policy override review.",
                tool_results,
            )

        refund = self._execute_tool(
            "process_refund",
            {
                "order_id": order_id,
                "amount": float(order_data["amount"]),
                "reason": "Approved return within policy window",
                "actor_role": actor_role,
            },
        )
        tool_results.append(refund)

        if refund.get("ok"):
            refund_id = refund["data"]["refund_id"]
            return self._build_response("resolved", f"Return approved and refund {refund_id} created.", tool_results)

        esc = self._execute_tool(
            "escalate_to_human",
            {
                "customer_id": customer_id,
                "reason": "Refund blocked by role/policy",
                "priority": "high",
                "context": {"order_id": order_id, "refund_error": refund},
            },
        )
        tool_results.append(esc)
        return self._build_response(
            "escalated",
            "Return eligible but refund authorization blocked; escalated.",
            tool_results,
        )

    def _resolve_billing_dispute(self, customer_id: str, order_id: str, actor_role: str) -> Dict[str, Any]:
        tool_results: List[Dict[str, Any]] = []
        cust = self._execute_tool("get_customer", {"customer_id": customer_id})
        order = self._execute_tool("lookup_order", {"order_id": order_id})
        tool_results.extend([cust, order])

        if not cust.get("ok") or not order.get("ok"):
            return self._build_response("escalated", "Unable to validate billing context; escalated.", tool_results)

        dispute = float(order["data"].get("billing_dispute", 0.0))
        if dispute <= 0:
            return self._build_response("resolved", "No billing discrepancy found on this order.", tool_results)

        if dispute <= self.auto_refund_limit:
            refund = self._execute_tool(
                "process_refund",
                {
                    "order_id": order_id,
                    "amount": dispute,
                    "reason": "Billing dispute auto-resolution",
                    "actor_role": actor_role,
                },
            )
            tool_results.append(refund)
            if refund.get("ok"):
                return self._build_response(
                    "resolved",
                    f"Billing issue resolved with refund {refund['data']['refund_id']} for {dispute:.2f}.",
                    tool_results,
                )

        esc = self._execute_tool(
            "escalate_to_human",
            {
                "customer_id": customer_id,
                "reason": "Large or blocked billing dispute",
                "priority": "high",
                "context": {"order_id": order_id, "dispute": dispute},
            },
        )
        tool_results.append(esc)
        return self._build_response("escalated", "Billing dispute requires manual investigation; escalated.", tool_results)

    def _resolve_account_issue(self, customer_id: str) -> Dict[str, Any]:
        tool_results: List[Dict[str, Any]] = []
        cust = self._execute_tool("get_customer", {"customer_id": customer_id})
        tool_results.append(cust)
        if not cust.get("ok"):
            return self._build_response("escalated", "Account not found; escalated.", tool_results)

        customer = cust["data"]
        if customer["status"] == "locked":
            esc = self._execute_tool(
                "escalate_to_human",
                {
                    "customer_id": customer_id,
                    "reason": "Account lockout requires identity verification",
                    "priority": "high",
                    "context": {"status": customer["status"]},
                },
            )
            tool_results.append(esc)
            return self._build_response("escalated", "Account is locked and needs specialist verification.", tool_results)

        if not customer["email_verified"]:
            esc = self._execute_tool(
                "escalate_to_human",
                {
                    "customer_id": customer_id,
                    "reason": "Unverified email blocks self-service recovery",
                    "priority": "medium",
                    "context": {"email_verified": False},
                },
            )
            tool_results.append(esc)
            return self._build_response(
                "escalated",
                "Account exists but email is unverified; escalated for secure verification.",
                tool_results,
            )

        return self._build_response("resolved", "Account is active. Guided customer through self-service reset path.", tool_results)

    def handle_request(self, user_message: str, actor_role: str = "agent") -> Dict[str, Any]:
        text = user_message.lower()
        customer_id = self._extract_id(user_message, "C")
        order_id = self._extract_id(user_message, "O")

        if "return" in text:
            if not customer_id or not order_id:
                return self._build_response(
                    "escalated",
                    "Missing customer/order identifiers for return request; escalated.",
                    [],
                )
            return self._resolve_return(customer_id, order_id, actor_role)

        if "billing" in text or "charged" in text or "invoice" in text:
            if not customer_id or not order_id:
                return self._build_response(
                    "escalated",
                    "Missing customer/order identifiers for billing dispute; escalated.",
                    [],
                )
            return self._resolve_billing_dispute(customer_id, order_id, actor_role)

        if "account" in text or "locked" in text or "login" in text:
            if not customer_id:
                return self._build_response(
                    "escalated",
                    "Missing customer identifier for account issue; escalated.",
                    [],
                )
            return self._resolve_account_issue(customer_id)

        if customer_id:
            esc = self._execute_tool(
                "escalate_to_human",
                {
                    "customer_id": customer_id,
                    "reason": "High ambiguity request outside supported domains",
                    "priority": "medium",
                    "context": {"message": user_message},
                },
            )
            return self._build_response("escalated", "Request is too ambiguous; escalated to human.", [esc])

        return self._build_response("escalated", "Unable to identify customer context; escalated.", [])


def build_runtime(
    db_path: str = "support_mock.db",
    reset_db: bool = False,
    verbose: bool = False,
    trace_sink: Optional[Callable[[str], None]] = print,
) -> Tuple[SupportMCPAgent, MCPMockServer, SQLiteSupportRepository]:
    repo = SQLiteSupportRepository(db_path=db_path, reset=reset_db)
    server = MCPMockServer(verbose=verbose)

    def _log_event(event: Dict[str, Any]) -> None:
        repo.log_tool_call(
            tool_name=event["tool"],
            args=event["args"],
            ok=event["ok"],
            error_category=event.get("error_category"),
            error_description=event.get("error_description"),
            forced_failure=event.get("forced_failure", False),
            latency_ms=int(event.get("latency_ms", 0)),
        )

    server.set_event_sink(_log_event)

    def get_customer(customer_id: str) -> Dict[str, Any]:
        customer = repo.get_customer(customer_id)
        if customer is None:
            raise ToolError("validation", False, f"Customer '{customer_id}' not found.")
        return customer

    def lookup_order(order_id: str) -> Dict[str, Any]:
        order = repo.get_order(order_id)
        if order is None:
            raise ToolError("validation", False, f"Order '{order_id}' not found.")
        return order

    def process_refund(order_id: str, amount: float, reason: str, actor_role: str) -> Dict[str, Any]:
        if actor_role not in {"agent", "manager"}:
            raise ToolError("permission", False, "actor_role must be one of: agent, manager.")
        order = repo.get_order(order_id)
        if order is None:
            raise ToolError("validation", False, f"Order '{order_id}' not found for refund.")
        if amount <= 0:
            raise ToolError("validation", False, "Refund amount must be greater than zero.")
        if actor_role == "agent" and amount > 200.0:
            raise ToolError("permission", False, "Agents may not approve refunds above 200 USD.")

        existing = repo.find_refund(order_id=order_id, amount=amount, reason=reason)
        if existing is not None:
            return existing

        return repo.create_refund(order_id=order_id, amount=amount, reason=reason, status="approved")

    def escalate_to_human(
        customer_id: str,
        reason: str,
        priority: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        if priority not in {"low", "medium", "high"}:
            raise ToolError("validation", False, "priority must be one of low, medium, high.")
        return repo.create_escalation(customer_id=customer_id, reason=reason, priority=priority, context=context)

    server.register_tool(
        ToolSpec(
            name="get_customer",
            description="Fetch customer profile and account status by customer_id.",
            input_schema={"customer_id": "string"},
            handler=get_customer,
        )
    )
    server.register_tool(
        ToolSpec(
            name="lookup_order",
            description="Fetch order details by order_id.",
            input_schema={"order_id": "string"},
            handler=lookup_order,
        )
    )
    server.register_tool(
        ToolSpec(
            name="process_refund",
            description="Attempt to create or reuse a refund record.",
            input_schema={
                "order_id": "string",
                "amount": "number",
                "reason": "string",
                "actor_role": "agent|manager",
            },
            handler=process_refund,
        )
    )
    server.register_tool(
        ToolSpec(
            name="escalate_to_human",
            description="Create a human escalation ticket with context.",
            input_schema={
                "customer_id": "string",
                "reason": "string",
                "priority": "low|medium|high",
                "context": "object (optional)",
            },
            handler=escalate_to_human,
        )
    )

    agent = SupportMCPAgent(
        mcp_server=server,
        return_window_days=30,
        auto_refund_limit=100.0,
        max_retries=1,
        verbose=verbose,
        trace_sink=trace_sink,
    )
    return agent, server, repo
