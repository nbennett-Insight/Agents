"""Exercise 1: Multi-tool agent with escalation logic.

This file implements:
1) MCP-style tool definitions with explicit boundaries.
2) Agentic loop driven by stop_reason values (tool_use/end_turn).
3) Structured tool errors with category and retry metadata.
4) Programmatic interception hook for business-rule escalation.
5) Multi-concern request decomposition and response synthesis.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple


# -----------------------------
# Structured errors and results
# -----------------------------


@dataclass
class ToolError(Exception):
    errorCategory: str  # transient | validation | permission
    isRetryable: bool
    description: str

    def to_payload(self) -> Dict[str, Any]:
        return {
            "ok": False,
            "errorCategory": self.errorCategory,
            "isRetryable": self.isRetryable,
            "description": self.description,
        }


@dataclass
class ToolSpec:
    name: str
    description: str
    input_schema: Dict[str, str]
    boundary_conditions: List[str]


@dataclass
class ToolCall:
    tool_name: str
    args: Dict[str, Any]


@dataclass
class ModelStep:
    stop_reason: str  # tool_use | end_turn
    tool_calls: List[ToolCall]
    final_message: Optional[str] = None


class InMemoryServices:
    """Small deterministic service layer used by tool functions."""

    def __init__(self) -> None:
        self.account_balances = {
            "A100": 214.33,
            "A200": -51.0,
            "A300": 880.77,
        }
        self.invoice_balances = {
            ("CUST-01", "2026-04"): 403.2,
            ("CUST-01", "2026-05"): 100.0,
            ("CUST-99", "2026-05"): 0.0,
        }
        self._invoice_attempts: Dict[Tuple[str, str], int] = {}
        self.tickets: List[Dict[str, Any]] = []

    def get_account_balance(self, account_id: str) -> float:
        if not account_id.startswith("A"):
            raise ToolError(
                errorCategory="validation",
                isRetryable=False,
                description="account_id must begin with 'A' (example: A100).",
            )
        if account_id not in self.account_balances:
            raise ToolError(
                errorCategory="validation",
                isRetryable=False,
                description=f"No account exists for account_id '{account_id}'.",
            )
        return self.account_balances[account_id]

    def get_invoice_balance(self, customer_id: str, month: str) -> float:
        key = (customer_id, month)

        # Deterministic transient simulation for retry behavior.
        if key == ("CUST-01", "2026-04"):
            self._invoice_attempts[key] = self._invoice_attempts.get(key, 0) + 1
            if self._invoice_attempts[key] == 1:
                raise ToolError(
                    errorCategory="transient",
                    isRetryable=True,
                    description="Invoice service timed out. Retry should succeed.",
                )

        if key not in self.invoice_balances:
            raise ToolError(
                errorCategory="validation",
                isRetryable=False,
                description=(
                    "No invoice balance found for this customer and month. "
                    "Expected month format YYYY-MM."
                ),
            )
        return self.invoice_balances[key]

    def submit_refund(self, account_id: str, amount: float, actor_role: str) -> Dict[str, Any]:
        if amount <= 0:
            raise ToolError(
                errorCategory="validation",
                isRetryable=False,
                description="Refund amount must be greater than zero.",
            )
        if actor_role not in {"agent", "manager"}:
            raise ToolError(
                errorCategory="permission",
                isRetryable=False,
                description="Only support agent or manager roles can submit refunds.",
            )
        if actor_role == "agent" and amount > 500:
            raise ToolError(
                errorCategory="permission",
                isRetryable=False,
                description="Agent role can only submit refunds up to 500.",
            )
        return {
            "refundId": f"R-{account_id}-{int(amount * 100)}",
            "status": "submitted",
            "amount": amount,
        }

    def create_support_ticket(
        self,
        issue: str,
        severity: str = "medium",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        if severity not in {"low", "medium", "high"}:
            raise ToolError(
                errorCategory="validation",
                isRetryable=False,
                description="severity must be one of low, medium, high.",
            )
        ticket = {
            "ticketId": f"T-{len(self.tickets) + 1:04d}",
            "issue": issue,
            "severity": severity,
            "metadata": metadata or {},
            "status": "open",
        }
        self.tickets.append(ticket)
        return ticket


class MultiToolAgent:
    def __init__(self, escalation_threshold: float = 1000.0, max_retries: int = 2) -> None:
        self.services = InMemoryServices()
        self.escalation_threshold = escalation_threshold
        self.max_retries = max_retries

        # Step 1: MCP-style tool definitions with clear distinctions.
        self.tool_specs: List[ToolSpec] = [
            ToolSpec(
                name="get_account_balance",
                description=(
                    "Returns current account-level balance for one account_id. "
                    "Use for account ledger checks, not monthly billing."
                ),
                input_schema={"account_id": "string (example: A100)"},
                boundary_conditions=[
                    "Accepts only account IDs beginning with 'A'.",
                    "Does not provide invoice/month-level details.",
                    "Validation error if account is missing.",
                ],
            ),
            ToolSpec(
                name="get_invoice_balance",
                description=(
                    "Returns customer invoice balance for a specific month. "
                    "Use for billing-cycle invoice checks, not account ledger totals."
                ),
                input_schema={
                    "customer_id": "string (example: CUST-01)",
                    "month": "string YYYY-MM",
                },
                boundary_conditions=[
                    "May emit transient timeout; caller should retry.",
                    "Requires exact month format YYYY-MM.",
                    "Does not accept account_id in place of customer_id.",
                ],
            ),
            ToolSpec(
                name="submit_refund",
                description=(
                    "Submits a refund request for an account. "
                    "Subject to role permissions and escalation threshold."
                ),
                input_schema={
                    "account_id": "string",
                    "amount": "number > 0",
                    "actor_role": "agent|manager",
                },
                boundary_conditions=[
                    "Permission error if actor role is unauthorized.",
                    "Validation error if amount <= 0.",
                    "Business hook can reroute large refunds to escalation workflow.",
                ],
            ),
            ToolSpec(
                name="create_support_ticket",
                description="Creates a support/escalation ticket for human follow-up.",
                input_schema={
                    "issue": "string",
                    "severity": "low|medium|high",
                    "metadata": "object (optional)",
                },
                boundary_conditions=[
                    "Not for account data retrieval.",
                    "Not for direct refund processing.",
                    "Validation error for invalid severity values.",
                ],
            ),
        ]

        self.tool_impls: Dict[str, Callable[..., Any]] = {
            "get_account_balance": self.services.get_account_balance,
            "get_invoice_balance": self.services.get_invoice_balance,
            "submit_refund": self.services.submit_refund,
            "create_support_ticket": self.services.create_support_ticket,
        }

    # -----------------------------
    # Step 4: Programmatic intercept
    # -----------------------------

    def intercept_tool_call(self, call: ToolCall) -> Tuple[Optional[Dict[str, Any]], ToolCall]:
        if call.tool_name != "submit_refund":
            return None, call

        amount = float(call.args.get("amount", 0))
        if amount <= self.escalation_threshold:
            return None, call

        ticket = self.services.create_support_ticket(
            issue="Refund amount exceeded auto-processing threshold",
            severity="high",
            metadata={
                "originalTool": call.tool_name,
                "originalArgs": call.args,
                "threshold": self.escalation_threshold,
            },
        )
        intercepted_result = {
            "ok": True,
            "intercepted": True,
            "escalated": True,
            "reason": (
                f"Blocked refund above threshold {self.escalation_threshold:.2f}; "
                "escalated to human review."
            ),
            "ticket": ticket,
        }
        return intercepted_result, call

    # --------------------------------
    # Step 3: Structured error handling
    # --------------------------------

    def execute_tool(self, call: ToolCall) -> Dict[str, Any]:
        intercepted_result, _ = self.intercept_tool_call(call)
        if intercepted_result is not None:
            return intercepted_result

        impl = self.tool_impls.get(call.tool_name)
        if impl is None:
            return {
                "ok": False,
                "errorCategory": "validation",
                "isRetryable": False,
                "description": f"Unknown tool '{call.tool_name}'.",
            }

        attempt = 0
        while True:
            try:
                data = impl(**call.args)
                return {"ok": True, "tool": call.tool_name, "data": data}
            except ToolError as err:
                if err.errorCategory == "transient" and err.isRetryable and attempt < self.max_retries:
                    attempt += 1
                    continue
                return err.to_payload()
            except Exception as err:
                return {
                    "ok": False,
                    "errorCategory": "transient",
                    "isRetryable": False,
                    "description": f"Unhandled tool exception: {err}",
                }

    # -------------------------------------------------
    # Step 2 + 5: Agentic loop and concern decomposition
    # -------------------------------------------------

    def _plan_concerns(self, user_message: str, actor_role: str) -> List[ToolCall]:
        m = user_message.lower()
        calls: List[ToolCall] = []

        # Simple multi-concern decomposition for training/demo.
        if "account balance" in m:
            account_id = "A100" if "a100" in m else "A200" if "a200" in m else "A100"
            calls.append(ToolCall("get_account_balance", {"account_id": account_id}))

        if "invoice" in m:
            customer_id = "CUST-01" if "cust-01" in m else "CUST-99" if "cust-99" in m else "CUST-01"
            month = "2026-04" if "2026-04" in m else "2026-05" if "2026-05" in m else "2026-04"
            calls.append(
                ToolCall(
                    "get_invoice_balance",
                    {"customer_id": customer_id, "month": month},
                )
            )

        if "refund" in m:
            amount = 1200.0 if "1200" in m else 150.0 if "150" in m else 600.0
            account_id = "A100" if "a100" in m else "A200" if "a200" in m else "A100"
            calls.append(
                ToolCall(
                    "submit_refund",
                    {"account_id": account_id, "amount": amount, "actor_role": actor_role},
                )
            )

        if "ticket" in m and "refund" not in m:
            calls.append(
                ToolCall(
                    "create_support_ticket",
                    {
                        "issue": "User requested manual support ticket",
                        "severity": "medium",
                        "metadata": {"source": "direct_user_request"},
                    },
                )
            )

        return calls

    def _next_model_step(self, pending_calls: List[ToolCall], final_message: str) -> ModelStep:
        if pending_calls:
            return ModelStep(stop_reason="tool_use", tool_calls=[pending_calls.pop(0)])
        return ModelStep(stop_reason="end_turn", tool_calls=[], final_message=final_message)

    def _synthesize(self, user_message: str, results: List[Dict[str, Any]]) -> str:
        lines = [f"Request handled: {user_message}", ""]
        for idx, item in enumerate(results, start=1):
            if item.get("ok"):
                if item.get("intercepted"):
                    ticket_id = item["ticket"]["ticketId"]
                    lines.append(
                        f"{idx}. Escalation triggered: {item['reason']} Ticket {ticket_id} created."
                    )
                else:
                    lines.append(f"{idx}. Success from {item.get('tool')}: {item.get('data')}")
            else:
                category = item.get("errorCategory")
                retryable = item.get("isRetryable")
                description = item.get("description")
                lines.append(
                    f"{idx}. Error [{category}, retryable={retryable}]: {description}"
                )

        lines.append("")
        lines.append("Unified response: all detected concerns were processed in one pass.")
        return "\n".join(lines)

    def run(self, user_message: str, actor_role: str = "agent") -> Dict[str, Any]:
        pending_calls = self._plan_concerns(user_message, actor_role=actor_role)
        tool_results: List[Dict[str, Any]] = []

        # Exercise requirement: explicit stop_reason loop.
        while True:
            step = self._next_model_step(
                pending_calls,
                final_message="All requested operations are complete.",
            )

            if step.stop_reason == "tool_use":
                for call in step.tool_calls:
                    result = self.execute_tool(call)
                    tool_results.append(result)
                continue

            if step.stop_reason == "end_turn":
                final_text = self._synthesize(user_message, tool_results)
                return {
                    "stop_reason": "end_turn",
                    "message": final_text,
                    "tool_results": tool_results,
                }

            return {
                "stop_reason": "end_turn",
                "message": "Agent ended due to unsupported stop_reason.",
                "tool_results": tool_results,
            }


def run_demo() -> None:
    agent = MultiToolAgent(escalation_threshold=1000.0, max_retries=2)

    cases = [
        {
            "name": "Multi-concern with escalation + transient retry",
            "message": (
                "Please check account balance for A100, invoice for CUST-01 in 2026-04, "
                "and submit refund 1200 for A100."
            ),
            "role": "agent",
        },
        {
            "name": "Permission business error",
            "message": "Please submit refund 600 for A100.",
            "role": "agent",
        },
        {
            "name": "Normal successful flow",
            "message": "Check account balance for A200 and invoice for CUST-99 in 2026-05.",
            "role": "manager",
        },
    ]

    for case in cases:
        print("=" * 80)
        print(case["name"])
        out = agent.run(case["message"], actor_role=case["role"])
        print(out["message"])


if __name__ == "__main__":
    run_demo()
