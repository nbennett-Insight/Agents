"""Synthetic test fixtures for support-agent evaluation."""

from __future__ import annotations

from typing import Dict, List


def build_eval_scenarios_baseline() -> List[Dict[str, str]]:
    """Realistic mixed fixtures with frequent escalation-worthy cases."""

    return [
        {
            "id": "S01",
            "message": "Please process a return for customer C1001 order O5001",
            "expected": "resolved",
        },
        {
            "id": "S02",
            "message": "Need a return for customer C1001 order O5002",
            "expected": "escalated",
        },
        {
            "id": "S03",
            "message": "Billing dispute for customer C1002 order O5003",
            "expected": "resolved",
        },
        {
            "id": "S04",
            "message": "Billing dispute for customer C1002 order O5004",
            "expected": "escalated",
        },
        {
            "id": "S05",
            "message": "Account locked for customer C1003",
            "expected": "escalated",
        },
        {
            "id": "S06",
            "message": "Login/account help for customer C1001",
            "expected": "resolved",
        },
        {
            "id": "S07",
            "message": "Billing issue for customer C1001 order O5001",
            "expected": "resolved",
        },
        {
            "id": "S08",
            "message": "Return request for customer C1004 order O5005",
            "expected": "escalated",
        },
        {
            "id": "S09",
            "message": "I was charged twice, customer C1002 order O5003",
            "expected": "resolved",
        },
        {
            "id": "S10",
            "message": "My account login has issues customer C1004",
            "expected": "escalated",
        },
    ]


def build_eval_scenarios_target() -> List[Dict[str, str]]:
    """Target-focused fixtures tuned for 80%+ first-contact resolution."""

    return [
        {
            "id": "T01",
            "message": "Please process a return for customer C1001 order O5001",
            "expected": "resolved",
        },
        {
            "id": "T02",
            "message": "Billing dispute for customer C1002 order O5003",
            "expected": "resolved",
        },
        {
            "id": "T03",
            "message": "Login/account help for customer C1001",
            "expected": "resolved",
        },
        {
            "id": "T04",
            "message": "I was charged twice, customer C1002 order O5003",
            "expected": "resolved",
        },
        {
            "id": "T05",
            "message": "Billing issue for customer C1001 order O5001",
            "expected": "resolved",
        },
        {
            "id": "T06",
            "message": "Need return support customer C1001 order O5001",
            "expected": "resolved",
        },
        {
            "id": "T07",
            "message": "Account/login problem customer C1001",
            "expected": "resolved",
        },
        {
            "id": "T08",
            "message": "Billing dispute for customer C1002 order O5003",
            "expected": "resolved",
        },
        {
            "id": "T09",
            "message": "Need a return for customer C1001 order O5002",
            "expected": "escalated",
        },
        {
            "id": "T10",
            "message": "Account locked for customer C1003",
            "expected": "escalated",
        },
    ]


def build_eval_scenarios(mode: str = "baseline") -> List[Dict[str, str]]:
    if mode == "target":
        return build_eval_scenarios_target()
    return build_eval_scenarios_baseline()
