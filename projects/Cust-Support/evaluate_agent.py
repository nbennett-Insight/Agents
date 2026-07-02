"""Evaluation harness for first-contact resolution (FCR)."""

from __future__ import annotations

import argparse
from typing import Dict, List

from mock_data import build_eval_scenarios
from support_agent import SupportResolutionAgent


def evaluate(mode: str = "baseline") -> Dict[str, object]:
    agent = SupportResolutionAgent(return_window_days=30, auto_refund_limit=100.0)
    scenarios = build_eval_scenarios(mode=mode)

    rows: List[Dict[str, object]] = []
    resolved_count = 0
    expected_match_count = 0

    for case in scenarios:
        result = agent.handle_request(case["message"], actor_role="agent")
        outcome = str(result["outcome"])
        first_contact_resolved = bool(result["first_contact_resolved"])

        if first_contact_resolved:
            resolved_count += 1
        if outcome == case["expected"]:
            expected_match_count += 1

        rows.append(
            {
                "id": case["id"],
                "expected": case["expected"],
                "actual": outcome,
                "fcr": first_contact_resolved,
                "message": case["message"],
            }
        )

    total = len(scenarios)
    fcr = resolved_count / total if total else 0.0
    accuracy = expected_match_count / total if total else 0.0

    return {
        "mode": mode,
        "total": total,
        "resolved": resolved_count,
        "fcr": fcr,
        "expected_accuracy": accuracy,
        "rows": rows,
        "target_met": fcr >= 0.80,
    }


def print_report(mode: str = "baseline") -> None:
    report = evaluate(mode=mode)

    print("=" * 90)
    print("Customer Support Agent Evaluation")
    print("=" * 90)
    print(f"Scenario pack: {report['mode']}")
    print(f"Total scenarios: {report['total']}")
    print(f"First-contact resolved: {report['resolved']}")
    print(f"FCR: {report['fcr']:.2%}")
    print(f"Expected outcome match: {report['expected_accuracy']:.2%}")
    print(f"Meets 80%+ target: {report['target_met']}")
    print("-" * 90)

    for row in report["rows"]:
        status = "PASS" if row["expected"] == row["actual"] else "FAIL"
        print(
            f"{row['id']} {status} | expected={row['expected']:<9} actual={row['actual']:<9} "
            f"fcr={str(row['fcr']):<5} | {row['message']}"
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate support agent FCR and outcome accuracy.")
    parser.add_argument(
        "--mode",
        choices=["baseline", "target"],
        default="baseline",
        help="Scenario pack to run.",
    )
    args = parser.parse_args()
    print_report(mode=args.mode)
