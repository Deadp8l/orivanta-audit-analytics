"""Reference specification tests for the Orivanta authorization-control family.

This is an integration aid, not a replacement for the validated production pipeline.
It uses semantic field names so each scenario is independently understandable.
Map these specifications to the repository's exact source columns and production
functions before merging.

The T04 direct-difference reference uses the largest absolute mismatch across
available approved-amount sources. Confirm that this matches production logic.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

import pytest


CENT = Decimal("0.01")


def _money(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    return Decimal(str(value))


def is_posted(row: dict[str, Any]) -> bool:
    return row.get("credit_status") == "Posted"


def t01_above_authority_without_approval(row: dict[str, Any]) -> bool:
    """Flag posted amount > effective authority when approval is not Approved."""
    amount = _money(row.get("posted_amount"))
    authority = _money(row.get("effective_authority"))
    if not is_posted(row) or amount is None or authority is None:
        return False
    return amount > authority and row.get("approval_status") != "Approved"


def t02_missing_required_approval(row: dict[str, Any]) -> bool:
    """Require both a traceable approval ID and Approved status."""
    if not is_posted(row) or not bool(row.get("approval_required")):
        return False
    approval_id = str(row.get("approval_id") or "").strip()
    return not approval_id or row.get("approval_status") != "Approved"


def t03_approval_after_posting(row: dict[str, Any]) -> bool:
    """Current date-only rule: flag Approved decisions > 1 calendar day after posting."""
    if not is_posted(row) or row.get("approval_status") != "Approved":
        return False
    posting_date = row.get("posting_date")
    decision_date = row.get("decision_date")
    if not isinstance(posting_date, date) or not isinstance(decision_date, date):
        return False
    return (decision_date - posting_date).days > 1


def t04_amount_mismatch(row: dict[str, Any]) -> tuple[bool, Decimal]:
    """Compare posted amount to all available approved amounts using a $0.01 tolerance."""
    if not is_posted(row):
        return False, Decimal("0.00")
    posted = _money(row.get("posted_amount"))
    approved_values = [
        _money(row.get("credit_approved_amount")),
        _money(row.get("approval_table_amount")),
    ]
    approved_values = [v for v in approved_values if v is not None]
    if posted is None or not approved_values:
        return False, Decimal("0.00")
    largest_difference = max(abs(posted - approved) for approved in approved_values)
    if largest_difference > CENT:
        return True, largest_difference.quantize(CENT)
    return False, Decimal("0.00")


def t19_self_approval(row: dict[str, Any]) -> bool:
    """Compare stable IDs; blanks do not establish self-approval."""
    if not is_posted(row):
        return False
    agent_id = str(row.get("agent_id") or "").strip()
    if not agent_id:
        return False
    approver_ids = {
        str(row.get("credit_supervisor_id") or "").strip(),
        str(row.get("approval_supervisor_id") or "").strip(),
    }
    approver_ids.discard("")
    return agent_id in approver_ids


@pytest.mark.parametrize(
    ("row", "expected"),
    [
        ({"credit_status": "Posted", "posted_amount": "99.99", "effective_authority": "100", "approval_status": "Missing"}, False),
        ({"credit_status": "Posted", "posted_amount": "100", "effective_authority": "100", "approval_status": "Missing"}, False),
        ({"credit_status": "Posted", "posted_amount": "100.01", "effective_authority": "100", "approval_status": "Missing"}, True),
        ({"credit_status": "Posted", "posted_amount": "175", "effective_authority": "100", "approval_status": "Approved"}, False),
        ({"credit_status": "Posted", "posted_amount": "175", "effective_authority": "100", "approval_status": "Pending"}, True),
        ({"credit_status": "Denied", "posted_amount": "175", "effective_authority": "100", "approval_status": "Missing"}, False),
        ({"credit_status": "Posted", "posted_amount": "175", "effective_authority": None, "approval_status": "Missing"}, False),
    ],
)
def test_t01(row: dict[str, Any], expected: bool) -> None:
    assert t01_above_authority_without_approval(row) is expected


@pytest.mark.parametrize(
    ("row", "expected"),
    [
        ({"credit_status": "Posted", "approval_required": False, "approval_id": "", "approval_status": "Missing"}, False),
        ({"credit_status": "Posted", "approval_required": True, "approval_id": "APR1", "approval_status": "Approved"}, False),
        ({"credit_status": "Posted", "approval_required": True, "approval_id": "", "approval_status": "Approved"}, True),
        ({"credit_status": "Posted", "approval_required": True, "approval_id": "APR1", "approval_status": "Denied"}, True),
        ({"credit_status": "Posted", "approval_required": True, "approval_id": "APR1", "approval_status": "Pending"}, True),
        ({"credit_status": "Pending", "approval_required": True, "approval_id": "", "approval_status": "Missing"}, False),
    ],
)
def test_t02(row: dict[str, Any], expected: bool) -> None:
    assert t02_missing_required_approval(row) is expected


@pytest.mark.parametrize(
    ("row", "expected"),
    [
        ({"credit_status": "Posted", "approval_status": "Approved", "posting_date": date(2026, 1, 5), "decision_date": date(2026, 1, 4)}, False),
        ({"credit_status": "Posted", "approval_status": "Approved", "posting_date": date(2026, 1, 5), "decision_date": date(2026, 1, 5)}, False),
        ({"credit_status": "Posted", "approval_status": "Approved", "posting_date": date(2026, 1, 5), "decision_date": date(2026, 1, 6)}, False),
        ({"credit_status": "Posted", "approval_status": "Approved", "posting_date": date(2026, 1, 5), "decision_date": date(2026, 1, 7)}, True),
        ({"credit_status": "Posted", "approval_status": "Approved", "posting_date": date(2026, 1, 5), "decision_date": None}, False),
        ({"credit_status": "Posted", "approval_status": "Denied", "posting_date": date(2026, 1, 5), "decision_date": date(2026, 1, 9)}, False),
    ],
)
def test_t03(row: dict[str, Any], expected: bool) -> None:
    assert t03_approval_after_posting(row) is expected


@pytest.mark.parametrize(
    ("row", "expected_flag", "expected_difference"),
    [
        ({"credit_status": "Posted", "posted_amount": "50", "credit_approved_amount": "50", "approval_table_amount": "50"}, False, Decimal("0.00")),
        ({"credit_status": "Posted", "posted_amount": "50.01", "credit_approved_amount": "50", "approval_table_amount": None}, False, Decimal("0.00")),
        ({"credit_status": "Posted", "posted_amount": "50.02", "credit_approved_amount": "50", "approval_table_amount": None}, True, Decimal("0.02")),
        ({"credit_status": "Posted", "posted_amount": "40.87", "credit_approved_amount": "40.87", "approval_table_amount": "15.87"}, True, Decimal("25.00")),
        ({"credit_status": "Posted", "posted_amount": "100", "credit_approved_amount": "90", "approval_table_amount": "80"}, True, Decimal("20.00")),
        ({"credit_status": "Posted", "posted_amount": "50", "credit_approved_amount": None, "approval_table_amount": None}, False, Decimal("0.00")),
        ({"credit_status": "Denied", "posted_amount": "50", "credit_approved_amount": "10", "approval_table_amount": None}, False, Decimal("0.00")),
    ],
)
def test_t04(row: dict[str, Any], expected_flag: bool, expected_difference: Decimal) -> None:
    actual_flag, actual_difference = t04_amount_mismatch(row)
    assert actual_flag is expected_flag
    assert actual_difference == expected_difference


@pytest.mark.parametrize(
    ("row", "expected"),
    [
        ({"credit_status": "Posted", "agent_id": "AGT1", "credit_supervisor_id": "SUP1", "approval_supervisor_id": "SUP2"}, False),
        ({"credit_status": "Posted", "agent_id": "AGT1", "credit_supervisor_id": "AGT1", "approval_supervisor_id": "SUP2"}, True),
        ({"credit_status": "Posted", "agent_id": "AGT1", "credit_supervisor_id": "SUP1", "approval_supervisor_id": "AGT1"}, True),
        ({"credit_status": "Posted", "agent_id": "AGT1", "credit_supervisor_id": "", "approval_supervisor_id": ""}, False),
        ({"credit_status": "Posted", "agent_id": "AGT1", "credit_supervisor_id": "AGT2", "approval_supervisor_id": ""}, False),
        ({"credit_status": "Denied", "agent_id": "AGT1", "credit_supervisor_id": "AGT1", "approval_supervisor_id": ""}, False),
    ],
)
def test_t19(row: dict[str, Any], expected: bool) -> None:
    assert t19_self_approval(row) is expected
