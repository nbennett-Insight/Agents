"""Lightweight tests for Exercise 1 implementation.

Run:
python gEx.1-tests.py
"""

from pathlib import Path
import importlib.util
import sys


MODULE_PATH = Path(__file__).with_name("gEx.1-multi_tool_agent.py")
SPEC = importlib.util.spec_from_file_location("gex1_multi_tool_agent", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Could not load module from {MODULE_PATH}")
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)

MultiToolAgent = MODULE.MultiToolAgent
ToolCall = MODULE.ToolCall


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def test_transient_retry_and_escalation() -> None:
    agent = MultiToolAgent(escalation_threshold=1000.0, max_retries=2)
    out = agent.run(
        "Check account balance for A100, invoice for CUST-01 in 2026-04, and submit refund 1200 for A100.",
        actor_role="agent",
    )

    assert_true(out["stop_reason"] == "end_turn", "Expected stop_reason=end_turn")
    results = out["tool_results"]
    assert_true(len(results) == 3, "Expected three tool results for three concerns")

    invoice_result = results[1]
    assert_true(invoice_result.get("ok") is True, "Invoice call should succeed after retry")

    refund_result = results[2]
    assert_true(refund_result.get("intercepted") is True, "Refund should be intercepted")
    assert_true(refund_result.get("escalated") is True, "Refund should escalate")


def test_permission_error() -> None:
    agent = MultiToolAgent(escalation_threshold=1000.0, max_retries=1)
    out = agent.run("Please submit refund 600 for A100.", actor_role="agent")
    result = out["tool_results"][0]

    assert_true(result.get("ok") is False, "Expected permission error")
    assert_true(result.get("errorCategory") == "permission", "Wrong error category")
    assert_true(result.get("isRetryable") is False, "Permission error should not retry")


def test_validation_error() -> None:
    agent = MultiToolAgent(escalation_threshold=1000.0)
    result = agent.execute_tool(
        call=ToolCall("get_account_balance", {"account_id": "X123"})
    )

    assert_true(result.get("ok") is False, "Expected validation error")
    assert_true(result.get("errorCategory") == "validation", "Wrong error category")
    assert_true(result.get("isRetryable") is False, "Validation error should not retry")


def run_all() -> None:
    tests = [
        test_transient_retry_and_escalation,
        test_permission_error,
        test_validation_error,
    ]
    for t in tests:
        t()
        print(f"PASS: {t.__name__}")


if __name__ == "__main__":
    run_all()
