"""Reference specification tests for Orivanta transaction-accuracy and duplicate controls.

The functions below document the validated T05-T08 rule boundaries and selected
control-design enhancements. They do not replace the production audit pipeline.
The production repository must retain its validated record populations and amounts
when these scenarios are integrated.

Validated family:
- T05: credit exceeds linked original charge
- T06: exact duplicate credits
- T07: near-duplicate credit indicator
- T08: potential split-credit threshold indicator
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from decimal import Decimal
from typing import Any, Iterable

import pytest


CENT = Decimal("0.01")
NEAR_AMOUNT_TOLERANCE = Decimal("1.00")
NEAR_DAY_WINDOW = 3


def _money(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    return Decimal(str(value)).quantize(CENT)


def _posted(row: dict[str, Any]) -> bool:
    return row.get("credit_status") == "Posted"


def t05_credit_exceeds_original_charge(
    row: dict[str, Any],
) -> tuple[bool, Decimal]:
    """Flag a posted credit that exceeds its linked charge total."""
    if not _posted(row):
        return False, Decimal("0.00")
    credit = _money(row.get("credit_amount"))
    charge = _money(row.get("total_charge_amount"))
    if credit is None or charge is None:
        return False, Decimal("0.00")
    excess = (credit - charge).quantize(CENT)
    if excess > CENT:
        return True, excess
    return False, Decimal("0.00")


def _exact_fingerprint(row: dict[str, Any]) -> tuple[Any, ...] | None:
    required = (
        row.get("account_id"),
        row.get("original_charge_id"),
        _money(row.get("credit_amount")),
        row.get("posting_date"),
        row.get("reason_code"),
    )
    if any(value in (None, "") for value in required):
        return None
    return required


def t06_exact_duplicate_ids(rows: Iterable[dict[str, Any]]) -> set[str]:
    """Flag all but the first stable record in each exact posted-credit fingerprint."""
    groups: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if not _posted(row):
            continue
        fingerprint = _exact_fingerprint(row)
        if fingerprint is not None:
            groups[fingerprint].append(row)

    flagged: set[str] = set()
    for group_rows in groups.values():
        if len(group_rows) <= 1:
            continue
        ordered = sorted(
            group_rows,
            key=lambda r: (
                r.get("posting_sequence", 10**12),
                str(r.get("credit_id") or ""),
            ),
        )
        flagged.update(str(row["credit_id"]) for row in ordered[1:])
    return flagged


def _days_between(later: date, earlier: date) -> int:
    return (later - earlier).days


def t07_near_duplicate_ids(rows: Iterable[dict[str, Any]]) -> set[str]:
    """Flag a later posted credit within $1 and three days of a prior contextual match."""
    posted = [row for row in rows if _posted(row)]
    ordered = sorted(
        posted,
        key=lambda r: (
            r.get("posting_date") or date.min,
            r.get("posting_sequence", 10**12),
            str(r.get("credit_id") or ""),
        ),
    )

    flagged: set[str] = set()
    for index, current in enumerate(ordered):
        current_date = current.get("posting_date")
        current_amount = _money(current.get("credit_amount"))
        if not isinstance(current_date, date) or current_amount is None:
            continue
        context = (
            current.get("account_id"),
            current.get("agent_id"),
            current.get("reason_code"),
            current.get("original_charge_id"),
        )
        if any(value in (None, "") for value in context):
            continue

        for prior in ordered[:index]:
            prior_date = prior.get("posting_date")
            prior_amount = _money(prior.get("credit_amount"))
            prior_context = (
                prior.get("account_id"),
                prior.get("agent_id"),
                prior.get("reason_code"),
                prior.get("original_charge_id"),
            )
            if prior_context != context or not isinstance(prior_date, date) or prior_amount is None:
                continue
            gap = _days_between(current_date, prior_date)
            if 0 <= gap <= NEAR_DAY_WINDOW and abs(current_amount - prior_amount) <= NEAR_AMOUNT_TOLERANCE:
                flagged.add(str(current["credit_id"]))
                break
    return flagged


def _split_key(row: dict[str, Any]) -> tuple[Any, ...] | None:
    key = (
        row.get("account_id"),
        row.get("agent_id"),
        row.get("posting_date"),
        row.get("original_charge_id"),
    )
    if any(value in (None, "") for value in key):
        return None
    return key


def t08_split_credit_ids(rows: Iterable[dict[str, Any]]) -> set[str]:
    """Flag same-context posted groups whose individual credits are within authority but aggregate exceeds it."""
    groups: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if not _posted(row):
            continue
        key = _split_key(row)
        if key is not None:
            groups[key].append(row)

    flagged: set[str] = set()
    for group_rows in groups.values():
        if len(group_rows) < 2:
            continue
        amounts = [_money(row.get("credit_amount")) for row in group_rows]
        authorities = [_money(row.get("agent_authority_limit")) for row in group_rows]
        if any(value is None for value in amounts + authorities):
            continue
        if len(set(authorities)) != 1:
            continue
        authority = authorities[0]
        assert authority is not None
        typed_amounts = [value for value in amounts if value is not None]
        if all(value <= authority for value in typed_amounts) and sum(typed_amounts, Decimal("0.00")) > authority:
            flagged.update(str(row["credit_id"]) for row in group_rows)
    return flagged


def proposed_duplicate_control_allows(row: dict[str, Any]) -> bool:
    """Control-design enhancement: allow a correction only when a valid reversal link is evidenced."""
    return bool(row.get("valid_reversal_link"))


@pytest.mark.parametrize(
    ("row", "expected_flag", "expected_excess"),
    [
        ({"credit_status": "Posted", "credit_amount": "50.00", "total_charge_amount": "50.00"}, False, Decimal("0.00")),
        ({"credit_status": "Posted", "credit_amount": "50.01", "total_charge_amount": "50.00"}, False, Decimal("0.00")),
        ({"credit_status": "Posted", "credit_amount": "50.02", "total_charge_amount": "50.00"}, True, Decimal("0.02")),
        ({"credit_status": "Posted", "credit_amount": "75.00", "total_charge_amount": "25.00"}, True, Decimal("50.00")),
        ({"credit_status": "Pending", "credit_amount": "75.00", "total_charge_amount": "25.00"}, False, Decimal("0.00")),
        ({"credit_status": "Posted", "credit_amount": None, "total_charge_amount": "25.00"}, False, Decimal("0.00")),
        ({"credit_status": "Posted", "credit_amount": "75.00", "total_charge_amount": None}, False, Decimal("0.00")),
        ({"credit_status": "Posted", "credit_amount": "10.00", "total_charge_amount": "25.00"}, False, Decimal("0.00")),
    ],
)
def test_t05(row: dict[str, Any], expected_flag: bool, expected_excess: Decimal) -> None:
    actual_flag, actual_excess = t05_credit_exceeds_original_charge(row)
    assert actual_flag is expected_flag
    assert actual_excess == expected_excess


def _base_credit(
    credit_id: str,
    *,
    account: str = "ACC1",
    charge: str = "CHG1",
    amount: str = "25.00",
    posting: date = date(2026, 1, 5),
    reason: str = "RC1",
    status: str = "Posted",
    agent: str = "AGT1",
    authority: str = "100.00",
    sequence: int = 1,
) -> dict[str, Any]:
    return {
        "credit_id": credit_id,
        "credit_status": status,
        "account_id": account,
        "original_charge_id": charge,
        "credit_amount": amount,
        "posting_date": posting,
        "reason_code": reason,
        "agent_id": agent,
        "agent_authority_limit": authority,
        "posting_sequence": sequence,
    }


@pytest.mark.parametrize(
    ("rows", "expected"),
    [
        ([_base_credit("C1")], set()),
        ([_base_credit("C1", sequence=1), _base_credit("C2", sequence=2)], {"C2"}),
        ([_base_credit("C1"), _base_credit("C2", amount="25.01")], set()),
        ([_base_credit("C1"), _base_credit("C2", reason="RC2")], set()),
        ([_base_credit("C1"), _base_credit("C2", charge="CHG2")], set()),
        ([_base_credit("C1"), _base_credit("C2", posting=date(2026, 1, 6))], set()),
        ([_base_credit("C1"), _base_credit("C2", status="Denied")], set()),
        (
            [
                _base_credit("C1", sequence=1),
                _base_credit("C2", sequence=2),
                _base_credit("C3", sequence=3),
            ],
            {"C2", "C3"},
        ),
    ],
)
def test_t06(rows: list[dict[str, Any]], expected: set[str]) -> None:
    assert t06_exact_duplicate_ids(rows) == expected


@pytest.mark.parametrize(
    ("rows", "expected"),
    [
        ([_base_credit("C1")], set()),
        (
            [_base_credit("C1", posting=date(2026, 1, 5)), _base_credit("C2", posting=date(2026, 1, 8), sequence=2)],
            {"C2"},
        ),
        (
            [_base_credit("C1", amount="25.00"), _base_credit("C2", amount="26.00", sequence=2)],
            {"C2"},
        ),
        (
            [_base_credit("C1", amount="25.00"), _base_credit("C2", amount="26.01", sequence=2)],
            set(),
        ),
        (
            [_base_credit("C1", posting=date(2026, 1, 5)), _base_credit("C2", posting=date(2026, 1, 9), sequence=2)],
            set(),
        ),
        ([_base_credit("C1"), _base_credit("C2", agent="AGT2", sequence=2)], set()),
        ([_base_credit("C1"), _base_credit("C2", account="ACC2", sequence=2)], set()),
        ([_base_credit("C1"), _base_credit("C2", status="Pending", sequence=2)], set()),
        (
            [_base_credit("C1", posting=date(2026, 1, 5)), _base_credit("C2", posting=date(2026, 1, 5), sequence=2)],
            {"C2"},
        ),
    ],
)
def test_t07(rows: list[dict[str, Any]], expected: set[str]) -> None:
    assert t07_near_duplicate_ids(rows) == expected


@pytest.mark.parametrize(
    ("rows", "expected"),
    [
        ([_base_credit("C1", amount="75", authority="100")], set()),
        (
            [
                _base_credit("C1", amount="60", authority="100", sequence=1),
                _base_credit("C2", amount="50", authority="100", sequence=2),
            ],
            {"C1", "C2"},
        ),
        (
            [
                _base_credit("C1", amount="50", authority="100", sequence=1),
                _base_credit("C2", amount="50", authority="100", sequence=2),
            ],
            set(),
        ),
        (
            [
                _base_credit("C1", amount="101", authority="100", sequence=1),
                _base_credit("C2", amount="1", authority="100", sequence=2),
            ],
            set(),
        ),
        (
            [
                _base_credit("C1", amount="60", authority="100", sequence=1),
                _base_credit("C2", amount="50", authority="100", posting=date(2026, 1, 6), sequence=2),
            ],
            set(),
        ),
        (
            [
                _base_credit("C1", amount="60", authority="100", sequence=1),
                _base_credit("C2", amount="50", authority="100", agent="AGT2", sequence=2),
            ],
            set(),
        ),
        (
            [
                _base_credit("C1", amount="60", authority="100", sequence=1),
                _base_credit("C2", amount="50", authority="200", sequence=2),
            ],
            set(),
        ),
        (
            [
                _base_credit("C1", amount="60", authority="100", sequence=1),
                _base_credit("C2", amount="50", authority="100", status="Denied", sequence=2),
            ],
            set(),
        ),
        (
            [
                _base_credit("C1", amount="40", authority="100", sequence=1),
                _base_credit("C2", amount="40", authority="100", sequence=2),
                _base_credit("C3", amount="30", authority="100", sequence=3),
            ],
            {"C1", "C2", "C3"},
        ),
    ],
)
def test_t08(rows: list[dict[str, Any]], expected: set[str]) -> None:
    assert t08_split_credit_ids(rows) == expected


@pytest.mark.parametrize(
    ("row", "expected"),
    [
        ({"valid_reversal_link": True}, True),
        ({"valid_reversal_link": False}, False),
        ({}, False),
    ],
)
def test_proposed_reversal_aware_control(row: dict[str, Any], expected: bool) -> None:
    assert proposed_duplicate_control_allows(row) is expected
