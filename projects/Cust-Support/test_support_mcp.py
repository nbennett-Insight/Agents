"""Tests for MCP layer, SQLite repository, and MCP-backed agent runtime."""

from __future__ import annotations

from support_agent_mcp import build_runtime


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def test_mcp_tool_listing() -> None:
    agent, server, repo = build_runtime(db_path="test_support_mcp.db", reset_db=True, verbose=False, trace_sink=None)
    response = server.handle_mcp_request({"jsonrpc": "2.0", "id": "1", "method": "tools/list"})
    names = {item["name"] for item in response["result"]}
    assert_true("get_customer" in names, "Expected get_customer in tools/list")
    assert_true("process_refund" in names, "Expected process_refund in tools/list")
    repo.close()


def test_injected_failure_and_fix() -> None:
    agent, server, repo = build_runtime(db_path="test_support_mcp.db", reset_db=True, verbose=False, trace_sink=None)

    server.inject_failure(
        tool_name="lookup_order",
        error_category="transient",
        is_retryable=False,
        description="Injected lookup failure",
        mode="always",
    )

    out_fail = agent.handle_request("Return customer C1001 order O5001", actor_role="agent")
    assert_true(out_fail["outcome"] == "escalated", "Expected escalation when lookup_order is forced to fail")

    server.clear_failure("lookup_order")
    out_ok = agent.handle_request("Return customer C1001 order O5001", actor_role="agent")
    assert_true(out_ok["outcome"] == "resolved", "Expected resolution after clearing forced failure")
    repo.close()


def test_tool_logs_persisted() -> None:
    agent, server, repo = build_runtime(db_path="test_support_mcp.db", reset_db=True, verbose=False, trace_sink=None)

    agent.handle_request("Billing dispute for customer C1002 order O5003", actor_role="agent")
    rows = repo.recent_tool_logs(limit=10)

    assert_true(len(rows) >= 2, "Expected at least two tool logs for billing flow")
    assert_true(any(r["tool_name"] == "get_customer" for r in rows), "Expected get_customer call in logs")
    assert_true(any(r["tool_name"] == "lookup_order" for r in rows), "Expected lookup_order call in logs")

    repo.close()


def run_all() -> None:
    tests = [
        test_mcp_tool_listing,
        test_injected_failure_and_fix,
        test_tool_logs_persisted,
    ]
    for t in tests:
        t()
        print(f"PASS: {t.__name__}")


if __name__ == "__main__":
    run_all()
