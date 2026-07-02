"""Lightweight tests for the customer support resolution lab."""

from __future__ import annotations

from evaluate_agent import evaluate
from support_agent import SupportResolutionAgent


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def test_return_within_window_resolves() -> None:
    agent = SupportResolutionAgent()
    out = agent.handle_request("Return customer C1001 order O5001", actor_role="agent")
    assert_true(out["outcome"] == "resolved", "Expected in-window return to resolve")


def test_return_expired_escalates() -> None:
    agent = SupportResolutionAgent()
    out = agent.handle_request("Return customer C1001 order O5002", actor_role="agent")
    assert_true(out["outcome"] == "escalated", "Expected expired return to escalate")


def test_billing_small_dispute_resolves() -> None:
    agent = SupportResolutionAgent()
    out = agent.handle_request("Billing dispute customer C1002 order O5003", actor_role="agent")
    assert_true(out["outcome"] == "resolved", "Expected small dispute to auto-resolve")


def test_account_locked_escalates() -> None:
    agent = SupportResolutionAgent()
    out = agent.handle_request("Account locked for customer C1003")
    assert_true(out["outcome"] == "escalated", "Expected locked account to escalate")


def test_eval_baseline_not_target() -> None:
    report = evaluate(mode="baseline")
    assert_true(report["target_met"] is False, "Baseline pack should not pass 80% target")
    assert_true(report["fcr"] == 0.5, "Expected deterministic FCR of 50% for baseline")


def test_eval_target_hits_target() -> None:
    report = evaluate(mode="target")
    assert_true(report["target_met"] is True, "Target pack should pass 80% target")
    assert_true(report["fcr"] == 0.8, "Expected deterministic FCR of 80% for target pack")


def run_all() -> None:
    tests = [
        test_return_within_window_resolves,
        test_return_expired_escalates,
        test_billing_small_dispute_resolves,
        test_account_locked_escalates,
        test_eval_baseline_not_target,
        test_eval_target_hits_target,
    ]

    for test in tests:
        test()
        print(f"PASS: {test.__name__}")


if __name__ == "__main__":
    run_all()
