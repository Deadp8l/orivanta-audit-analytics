from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict

import numpy as np
import pandas as pd

RUN_DATE = pd.Timestamp("2026-07-12")

EXCEPTION_COLUMNS = [
    "test_id", "risk_id", "control_id", "test_name", "exception_category", "exception_class",
    "severity", "confidence", "record_type", "record_id", "customer_id", "account_id", "agent_id",
    "supervisor_id", "charge_id", "credit_id", "payment_id", "case_id", "interaction_id",
    "exception_date", "transaction_amount", "gross_flagged_amount", "direct_measurable_amount",
    "investigative_amount", "expected_result", "actual_result", "detection_rule", "evidence",
    "additional_evidence_needed", "recommended_follow_up", "review_status", "reviewer_comments",
]


@dataclass(frozen=True)
class TestMeta:
    test_id: str
    risk_id: str
    control_id: str
    test_name: str
    exception_category: str
    exception_class: str
    severity: str
    confidence: str
    record_type: str
    expected_result: str
    detection_rule: str


def _bool(series: pd.Series) -> pd.Series:
    return series.astype("string").str.lower().isin(["1", "true", "yes", "y"])


def _numeric(series: pd.Series | np.ndarray | list | tuple | float | int, index: pd.Index) -> pd.Series:
    if isinstance(series, pd.Series):
        values = series.reset_index(drop=True)
        values.index = index
        return pd.to_numeric(values, errors="coerce").fillna(0.0).astype(float)
    if isinstance(series, (np.ndarray, list, tuple)):
        return pd.to_numeric(pd.Series(series, index=index), errors="coerce").fillna(0.0).astype(float)
    return pd.Series(float(series), index=index, dtype=float)


def _string(series: pd.Series | str, index: pd.Index) -> pd.Series:
    if isinstance(series, pd.Series):
        values = series.astype("string").fillna("").reset_index(drop=True)
        values.index = index
        return values
    return pd.Series(str(series), index=index, dtype="string")


def _build(
    frame: pd.DataFrame,
    meta: TestMeta,
    record_id_col: str,
    *,
    date_col: str | None = None,
    amount: pd.Series | float | int = 0.0,
    gross: pd.Series | float | int | None = None,
    direct: pd.Series | float | int = 0.0,
    investigative: pd.Series | float | int | None = None,
    evidence: pd.Series | str = "Structured-data exception generated from documented rule.",
    actual_result: pd.Series | str | None = None,
    follow_up: str = "Review the record, source documentation, authorization evidence, and management explanation.",
    additional_evidence: str = "Policy criteria, source-document support, system audit trail, and responsible-owner explanation.",
) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame(columns=EXCEPTION_COLUMNS)
    df = frame.copy().reset_index(drop=True)
    out = pd.DataFrame(index=df.index)
    out["test_id"] = meta.test_id
    out["risk_id"] = meta.risk_id
    out["control_id"] = meta.control_id
    out["test_name"] = meta.test_name
    out["exception_category"] = meta.exception_category
    out["exception_class"] = meta.exception_class
    out["severity"] = meta.severity
    out["confidence"] = meta.confidence
    out["record_type"] = meta.record_type
    out["record_id"] = _string(df[record_id_col] if record_id_col in df else "", df.index)
    for column in [
        "customer_id", "account_id", "agent_id", "supervisor_id", "charge_id", "credit_id",
        "payment_id", "case_id", "interaction_id",
    ]:
        out[column] = _string(df[column] if column in df else "", df.index)
    if date_col and date_col in df:
        out["exception_date"] = pd.to_datetime(df[date_col], errors="coerce").dt.strftime("%Y-%m-%d").fillna("")
    else:
        out["exception_date"] = ""
    amount_series = _numeric(amount, df.index).round(2)
    gross_series = _numeric(gross if gross is not None else amount_series.abs(), df.index).abs().round(2)
    direct_series = _numeric(direct, df.index).abs().round(2)
    investigative_series = _numeric(
        investigative if investigative is not None else np.where(direct_series > 0, 0.0, gross_series),
        df.index,
    ).abs().round(2)
    out["transaction_amount"] = amount_series
    out["gross_flagged_amount"] = gross_series
    out["direct_measurable_amount"] = direct_series
    out["investigative_amount"] = investigative_series
    out["expected_result"] = meta.expected_result
    out["actual_result"] = _string(actual_result if actual_result is not None else meta.exception_category, df.index)
    out["detection_rule"] = meta.detection_rule
    out["evidence"] = _string(evidence, df.index)
    out["additional_evidence_needed"] = additional_evidence
    out["recommended_follow_up"] = follow_up
    out["review_status"] = "Open"
    out["reviewer_comments"] = ""
    return out[EXCEPTION_COLUMNS]


def _add_exception_ids(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy().reset_index(drop=True)
    result.insert(0, "exception_id", [f"EXC-{index + 1:06d}" for index in range(len(result))])
    return result


META: dict[str, TestMeta] = {
    "T01": TestMeta("T01", "R01", "CTL001", "Credits above authority without approval", "CREDIT_ABOVE_AUTHORITY_NO_APPROVAL", "Control exception", "High", "High", "Credit", "Credits above agent authority have an approved authorization.", "Posted credit amount exceeds authority and approval status is not Approved."),
    "T02": TestMeta("T02", "R01", "CTL001", "Missing required approval", "REQUIRED_APPROVAL_MISSING", "Control exception", "High", "High", "Credit", "Every posted credit requiring approval has a valid approved approval record.", "Posted credit requires approval and has no approval ID or a nonapproved status."),
    "T03": TestMeta("T03", "R01", "CTL001", "Approval decision after posting", "APPROVAL_AFTER_POSTING", "Control exception", "High", "Moderate", "Credit", "Approval is completed before posting.", "Approved decision date is more than one calendar day after the posting date; one-day cases are excluded because posting is date-only."),
    "T04": TestMeta("T04", "R02", "CTL011", "Approved versus posted amount mismatch", "APPROVED_POSTED_AMOUNT_MISMATCH", "Control exception", "High", "High", "Credit", "Posted credit equals the approved amount.", "Posted amount differs from either the credit record approved amount or the linked approval approved amount by more than $0.01."),
    "T05": TestMeta("T05", "R03", "CTL002", "Credit exceeds original charge", "CREDIT_EXCEEDS_ORIGINAL_CHARGE", "Control exception", "Critical", "High", "Credit", "Credit does not exceed the linked original charge without separately documented authorization.", "Posted credit amount exceeds the linked charge total."),
    "T06": TestMeta("T06", "R04", "CTL003", "Exact duplicate credits", "DUPLICATE_CREDIT", "Control exception", "High", "High", "Credit", "No repeated materially identical posted credit exists.", "Later posted credit duplicates account, original charge, amount, posting date, and reason code."),
    "T07": TestMeta("T07", "R04", "CTL003", "Near-duplicate credits", "NEAR_DUPLICATE_CREDIT", "Behavioral risk indicator", "Moderate", "Moderate", "Credit", "Closely spaced, materially similar credits are reviewed for duplication.", "Later credit is within $1 and three days of a prior credit for the same account, agent, reason, and charge context."),
    "T08": TestMeta("T08", "R05", "CTL009", "Potential split-credit threshold avoidance", "SPLIT_CREDIT_THRESHOLD_AVOIDANCE", "Behavioral risk indicator", "High", "Moderate", "Credit", "Related same-day credits are aggregated before applying authority limits.", "Same account, agent, date, and charge context contains multiple individually within-limit credits whose combined amount exceeds authority."),
    "T09": TestMeta("T09", "R06", "CTL004", "Invalid or inactive reason code", "INVALID_REASON_CODE", "Data-quality issue", "Moderate", "High", "Credit", "Every credit uses an existing active reason code.", "Reason code is missing from the reason-code table or is inactive."),
    "T10": TestMeta("T10", "R06", "CTL004", "Reason code and credit type mismatch", "REASON_CODE_TYPE_MISMATCH", "Control exception", "Moderate", "High", "Credit", "Credit type agrees with the reason-code master.", "Credit type differs from the type assigned to the reason code."),
    "T11": TestMeta("T11", "R07", "CTL005", "Missing case support", "NO_SUPPORTING_CASE", "Control exception", "High", "High", "Credit", "A linked customer interaction has a valid supporting case.", "Posted credit has an interaction but no valid case reference."),
    "T12": TestMeta("T12", "R07", "CTL005", "Missing interaction support", "NO_SUPPORTING_INTERACTION", "Control exception", "High", "High", "Credit", "A linked customer case has a valid supporting interaction.", "Posted credit has a case but no valid interaction reference."),
    "T13": TestMeta("T13", "R07", "CTL005", "Missing required documentation", "MISSING_DOCUMENTATION", "Control exception", "High", "High", "Credit", "Linked credits and cases contain required support.", "Posted credit with valid case and interaction has incomplete credit or case documentation."),
    "T14": TestMeta("T14", "R08", "CTL005", "Posted credit not communicated", "POSTED_CREDIT_NOT_COMMUNICATED", "Control exception", "Moderate", "High", "Credit", "Posted customer-facing credits are communicated to the customer.", "Posted credit has a linked interaction and customer-notified flag is false."),
    "T15": TestMeta("T15", "R09", "CTL006", "Authentication failure", "AUTHENTICATION_FAILURE", "Control exception", "Critical", "High", "Credit", "Authentication is completed before a linked protected adjustment.", "Posted credit has a linked interaction with authentication-completed flag false."),
    "T16": TestMeta("T16", "R10", "CTL007", "Manual override without approval", "MANUAL_OVERRIDE_NO_APPROVAL", "Control exception", "High", "High", "Credit", "Manual override has approved authorization.", "Posted manual override has approval status other than Approved."),
    "T17": TestMeta("T17", "R11", "CTL008", "After-hours credit without review", "AFTER_HOURS_NO_REVIEW", "Control exception", "Moderate", "Moderate", "Credit", "After-hours credit has approval or complete review documentation.", "Posted after-hours credit lacks approved status or complete documentation."),
    "T18": TestMeta("T18", "R12", "CTL016", "Inactive employee activity", "INACTIVE_AGENT_POSTING", "Control exception", "Critical", "Moderate", "Credit", "Only active employees process credits.", "Credit was processed by an employee currently marked inactive; termination effective date is unavailable."),
    "T19": TestMeta("T19", "R13", "CTL015", "Self-approval", "SELF_APPROVAL", "Control exception", "Critical", "High", "Credit", "The processing agent is not recorded as the supervising approver.", "Credit agent ID equals supervisor ID or linked approval supervisor ID."),
    "T20": TestMeta("T20", "R14", "CTL017", "Customer-account mismatch", "CREDIT_WRONG_CUSTOMER", "Control exception", "Critical", "High", "Credit", "Credit customer agrees with the account owner.", "Credit customer ID differs from account customer ID."),
    "T21": TestMeta("T21", "R15", "CTL018", "Agent credit concentration", "EXCESSIVE_AGENT_CREDIT_CONCENTRATION", "Behavioral risk indicator", "Moderate", "Low", "Agent", "Agent activity is consistent with role peers after normalizing for interactions.", "Agent is at or above the role-level 90th percentile for both credits per 100 interactions and credit dollars per interaction."),
    "T22": TestMeta("T22", "R15", "CTL018", "Repeated customer credits", "REPEATED_CUSTOMER_CREDITS", "Behavioral risk indicator", "Moderate", "Low", "Customer", "Customer credit activity is proportionate to posted charges.", "Customer has at least three credits and a credit-to-charge ratio at or above the 90th percentile."),
    "T23": TestMeta("T23", "R15", "CTL018", "Agent-customer pairing concentration", "SUSPICIOUS_AGENT_CUSTOMER_PAIRING", "Behavioral risk indicator", "Moderate", "Low", "AgentCustomerPair", "Agent-customer pair activity is not unusually concentrated.", "Pair has at least three credits and amount at or above the 95th percentile of qualifying pairs."),
    "T24": TestMeta("T24", "R16", "CTL010", "Promised adjustment not completed", "PROMISED_CREDIT_NOT_POSTED", "Control exception", "High", "Moderate", "Interaction", "Promised credit, refund, or promotion is completed and posted.", "Interaction records an uncompleted adjustment promise and no linked posted credit."),
    "T25": TestMeta("T25", "R16", "CTL010", "Promised amount mismatch", "PROMISE_AMOUNT_MISMATCH", "Control exception", "High", "Moderate", "Interaction", "Posted linked credit agrees with the promised amount.", "Completed promise has linked posted credit total differing from promised amount by more than $1."),
    "T26": TestMeta("T26", "R16", "CTL010", "Promise completed after due date", "PROMISE_COMPLETED_LATE", "Control exception", "Moderate", "Moderate", "Interaction", "Promised adjustment is completed by the promised date.", "Completed promise has a linked credit posted after the promised completion date."),
    "T27": TestMeta("T27", "R17", "CTL010", "Transcript refund request without posted credit", "TRANSCRIPT_REFUND_REQUEST_LEAD", "NLP review lead", "Moderate", "Low", "Interaction", "Refund request is resolved or linked to a posted adjustment.", "Transcript contains refund-request language but no linked posted credit."),
    "T28": TestMeta("T28", "R17", "CTL010", "Transcript promise not completed", "TRANSCRIPT_PROMISE_LEAD", "NLP review lead", "Moderate", "Low", "Interaction", "Transcript promise is reflected in completed action.", "Transcript contains promise language and structured action-completed flag is false."),
    "T29": TestMeta("T29", "R17", "CTL006", "Transcript lacks authentication evidence", "TRANSCRIPT_AUTHENTICATION_LEAD", "NLP review lead", "Moderate", "Low", "Interaction", "Credit-linked interaction contains authentication evidence.", "Credit-linked interaction has authentication flag false and transcript lacks compliance language."),
    "T30": TestMeta("T30", "R17", "CTL005", "Transcript contradicts agent notes", "COMPLAINT_CONTRADICTS_AGENT_NOTES", "NLP review lead", "Moderate", "Low", "Interaction", "Agent notes are consistent with customer statements.", "Transcript indicates dispute or refund request while notes state no concern or accepted all charges."),
    "T31": TestMeta("T31", "R17", "CTL005", "Summary inconsistent with interaction", "SUMMARY_INCONSISTENT_WITH_CASE", "Data-quality issue", "Moderate", "Moderate", "Interaction", "Summary accurately reflects the structured contact reason.", "Expected contact-reason phrase is absent from the interaction summary."),
    "T32": TestMeta("T32", "R18", "CTL005", "Copied notes across cases", "COPIED_NOTES_ACROSS_CASES", "NLP review lead", "Low", "Low", "Interaction", "Agent notes are case-specific and not reused across unrelated cases.", "Exact non-generic note is repeated across multiple cases and either the same agent or same account."),
    "T33": TestMeta("T33", "R19", "CTL012", "Closed case without resolution evidence", "CLOSED_CASE_NO_RESOLUTION", "Control exception", "Moderate", "High", "Case", "Closed cases contain resolution code and summary.", "Closed case has blank resolution code or resolution summary."),
    "T34": TestMeta("T34", "R20", "CTL019", "Promotion outside effective period", "PROMOTION_OUTSIDE_EFFECTIVE_PERIOD", "Control exception", "Moderate", "High", "Credit", "Promotional adjustment is within the linked promotion effective dates.", "Promotional credit is linked to a promotion product and credit date is outside its effective dates."),
    "T35": TestMeta("T35", "R21", "CTL020", "Service credit lacks outage evidence", "SERVICE_CREDIT_NO_OUTAGE_EVIDENCE", "Control exception", "High", "High", "Credit", "Linked service-interruption case is validated and documented.", "Service-interruption credit has a linked case that is not a validated documented service-interruption dispute."),
    "T36": TestMeta("T36", "R22", "CTL013", "Payment reversal invalid original", "REVERSAL_WITHOUT_VALID_ORIGINAL", "Data-quality issue", "High", "High", "Payment", "Nonblank original-payment reference points to a valid payment.", "Reversed payment contains a nonblank invalid original-payment reference."),
    "T37": TestMeta("T37", "R22", "CTL013", "Charge reversal invalid original", "CHARGE_REVERSAL_INVALID_ORIGINAL", "Data-quality issue", "High", "High", "Charge", "Charge reversal references a valid original charge.", "Reversal charge has blank or invalid original-charge reference."),
    "T38": TestMeta("T38", "R04", "CTL003", "Duplicate charges", "DUPLICATE_CHARGE", "Control exception", "High", "High", "Charge", "No later materially identical posted charge exists.", "Later posted charge duplicates account, product, amount, posting date, and charge type."),
    "T39": TestMeta("T39", "R23", "CTL014", "Account reconciliation difference", "ACCOUNT_RECONCILIATION_DIFFERENCE", "Control exception", "Critical", "High", "Account", "Recorded closing balance agrees with expected closing balance.", "Absolute reconciliation difference exceeds $0.01."),
    "T40": TestMeta("T40", "R23", "CTL014", "Negative or impossible balance condition", "UNEXPECTED_BALANCE_CONDITION", "Data-quality issue", "High", "Moderate", "Account", "Account balances remain within plausible boundaries and past-due balance is consistent.", "Current balance is below -$500 or past-due balance exceeds absolute current balance by more than $1,000."),
}


def test_credit_authority(t: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    c = t["credits_adjustments"]
    rows = c[(c.credit_status == "Posted") & (c.credit_amount > c.agent_authority_limit) & (c.approval_status != "Approved")].copy()
    evidence = rows.apply(lambda r: f"amount={r.credit_amount:.2f}; authority={r.agent_authority_limit:.2f}; approval_status={r.approval_status}", axis=1)
    return _build(rows, META["T01"], "credit_id", date_col="posting_date", amount=rows.credit_amount, evidence=evidence)


def test_missing_approval(t: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    c = t["credits_adjustments"]
    rows = c[(c.credit_status == "Posted") & _bool(c.approval_required_flag) & ((c.approval_id == "") | c.approval_status.isin(["Missing", "Denied", "Pending"]))].copy()
    evidence = rows.apply(lambda r: f"approval_required=1; approval_id={r.approval_id}; approval_status={r.approval_status}", axis=1)
    return _build(rows, META["T02"], "credit_id", date_col="posting_date", amount=rows.credit_amount, evidence=evidence)


def test_approval_after_posting(t: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    c = t["credits_adjustments"]
    approvals = t["approvals"][["approval_id", "approval_decision_date", "approval_status"]].rename(columns={"approval_status": "approval_table_status"})
    rows = c.merge(approvals, on="approval_id", how="left")
    calendar_lag = rows.approval_decision_date.dt.normalize() - rows.posting_date.dt.normalize()
    rows = rows[(rows.credit_status == "Posted") & (rows.approval_table_status == "Approved") & (calendar_lag > pd.Timedelta(days=1))].copy()
    lag_days = (rows.approval_decision_date.dt.normalize() - rows.posting_date.dt.normalize()).dt.days
    evidence = rows.apply(lambda r: f"posting_date={r.posting_date.date()}; decision_date={r.approval_decision_date.date()}", axis=1)
    return _build(rows, META["T03"], "credit_id", date_col="posting_date", amount=rows.credit_amount, evidence=evidence, actual_result="Approval completed more than one calendar day after posting.")


def test_amount_mismatch(t: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    c = t["credits_adjustments"]
    approvals = t["approvals"][["approval_id", "approved_amount"]].rename(columns={"approved_amount": "approval_table_amount"})
    merged = c.merge(approvals, on="approval_id", how="left")
    diff_credit = (merged.credit_amount - merged.approved_amount).abs()
    diff_approval = (merged.credit_amount - merged.approval_table_amount).abs()
    mask = (merged.credit_status == "Posted") & (merged.approval_status == "Approved") & ((diff_credit > 0.01) | (diff_approval > 0.01))
    rows = merged[mask].copy()
    direct = pd.concat([diff_credit[mask], diff_approval[mask]], axis=1).max(axis=1)
    evidence = rows.apply(lambda r: f"posted={r.credit_amount:.2f}; credit_approved={r.approved_amount:.2f}; approval_table={r.approval_table_amount if pd.notna(r.approval_table_amount) else 'missing'}", axis=1)
    return _build(rows, META["T04"], "credit_id", date_col="posting_date", amount=rows.credit_amount, direct=direct, investigative=0.0, evidence=evidence)


def test_credit_exceeds_charge(t: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    c = t["credits_adjustments"]
    charges = t["charges"][["charge_id", "total_charge_amount"]].rename(columns={"charge_id": "original_charge_id"})
    rows = c.merge(charges, on="original_charge_id", how="inner")
    rows = rows[(rows.credit_status == "Posted") & (rows.credit_amount > rows.total_charge_amount)].copy()
    rows["charge_id"] = rows.original_charge_id
    direct = rows.credit_amount - rows.total_charge_amount
    evidence = rows.apply(lambda r: f"credit={r.credit_amount:.2f}; original_charge={r.total_charge_amount:.2f}; excess={r.credit_amount-r.total_charge_amount:.2f}", axis=1)
    return _build(rows, META["T05"], "credit_id", date_col="posting_date", amount=rows.credit_amount, direct=direct, investigative=0.0, evidence=evidence)


def test_exact_duplicate_credits(t: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    c = t["credits_adjustments"]
    keys = ["account_id", "original_charge_id", "credit_amount", "posting_date", "reason_code"]
    posted = c[c.credit_status == "Posted"].sort_values(keys + ["credit_id"]).copy()
    posted["duplicate_rank"] = posted.groupby(keys, dropna=False).cumcount()
    rows = posted[posted.duplicate_rank > 0].copy()
    evidence = rows.apply(lambda r: f"duplicate group: account={r.account_id}; charge={r.original_charge_id}; amount={r.credit_amount:.2f}; date={r.posting_date.date()}; reason={r.reason_code}", axis=1)
    return _build(rows, META["T06"], "credit_id", date_col="posting_date", amount=rows.credit_amount, direct=rows.credit_amount, investigative=0.0, evidence=evidence)


def test_near_duplicate_credits(t: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    c = t["credits_adjustments"]
    posted = c[c.credit_status == "Posted"].sort_values(["account_id", "agent_id", "reason_code", "original_charge_id", "posting_date", "credit_amount", "credit_id"]).copy()
    group = posted.groupby(["account_id", "agent_id", "reason_code", "original_charge_id"], dropna=False)
    posted["prior_credit_id"] = group.credit_id.shift()
    posted["prior_amount"] = group.credit_amount.shift()
    posted["prior_date"] = group.posting_date.shift()
    date_gap = (posted.posting_date - posted.prior_date).dt.days
    rows = posted[
        posted.prior_credit_id.notna()
        & ((posted.credit_amount - posted.prior_amount).abs() <= 1.0)
        & date_gap.between(0, 3)
        & ~((posted.credit_amount == posted.prior_amount) & (date_gap == 0))
    ].copy()
    evidence = rows.apply(lambda r: f"prior_credit={r.prior_credit_id}; current={r.credit_amount:.2f}; prior={r.prior_amount:.2f}; day_gap={(r.posting_date-r.prior_date).days}", axis=1)
    return _build(rows, META["T07"], "credit_id", date_col="posting_date", amount=rows.credit_amount, evidence=evidence)


def test_split_credits(t: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    c = t["credits_adjustments"]
    posted = c[c.credit_status == "Posted"].copy()
    keys = ["account_id", "agent_id", "posting_date", "original_charge_id"]
    groups = posted.groupby(keys, dropna=False).agg(
        group_count=("credit_id", "count"),
        group_amount=("credit_amount", "sum"),
        authority_limit=("agent_authority_limit", "max"),
        max_individual=("credit_amount", "max"),
    ).reset_index()
    groups = groups[(groups.group_count > 1) & (groups.group_amount > groups.authority_limit) & (groups.max_individual <= groups.authority_limit)]
    rows = posted.merge(groups, on=keys, how="inner")
    evidence = rows.apply(lambda r: f"group_count={r.group_count}; group_total={r.group_amount:.2f}; authority={r.authority_limit:.2f}", axis=1)
    return _build(rows, META["T08"], "credit_id", date_col="posting_date", amount=rows.credit_amount, evidence=evidence)


def test_invalid_reason_codes(t: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    c = t["credits_adjustments"]
    reasons = t["reason_codes"][["reason_code", "active_flag", "credit_type"]].rename(columns={"active_flag": "reason_active_flag", "credit_type": "reason_credit_type"})
    merged = c.merge(reasons, on="reason_code", how="left")
    rows = merged[merged.reason_credit_type.isna() | ~_bool(merged.reason_active_flag)].copy()
    posted_amount = np.where(rows.credit_status == "Posted", rows.credit_amount, 0.0)
    evidence = rows.apply(lambda r: f"reason_code={r.reason_code}; master_match={'no' if pd.isna(r.reason_credit_type) else 'yes'}; active={r.reason_active_flag}", axis=1)
    return _build(rows, META["T09"], "credit_id", date_col="posting_date", amount=rows.credit_amount, gross=posted_amount, investigative=posted_amount, evidence=evidence)


def test_reason_type_mismatch(t: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    c = t["credits_adjustments"]
    reasons = t["reason_codes"][["reason_code", "credit_type"]].rename(columns={"credit_type": "expected_credit_type"})
    rows = c.merge(reasons, on="reason_code", how="inner")
    rows = rows[(rows.credit_status == "Posted") & (rows.credit_type != rows.expected_credit_type)].copy()
    evidence = rows.apply(lambda r: f"actual_type={r.credit_type}; expected_type={r.expected_credit_type}; reason={r.reason_code}", axis=1)
    return _build(rows, META["T10"], "credit_id", date_col="posting_date", amount=rows.credit_amount, evidence=evidence)


def test_missing_case(t: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    c = t["credits_adjustments"]
    valid_cases = set(t["cases_disputes"].case_id.astype("string"))
    rows = c[(c.credit_status == "Posted") & (c.interaction_id != "") & ((c.case_id == "") | ~c.case_id.isin(valid_cases))].copy()
    evidence = rows.apply(lambda r: f"interaction_id={r.interaction_id}; case_id={r.case_id or 'blank'}", axis=1)
    return _build(rows, META["T11"], "credit_id", date_col="posting_date", amount=rows.credit_amount, evidence=evidence)


def test_missing_interaction(t: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    c = t["credits_adjustments"]
    valid_interactions = set(t["interactions"].interaction_id.astype("string"))
    rows = c[(c.credit_status == "Posted") & (c.case_id != "") & ((c.interaction_id == "") | ~c.interaction_id.isin(valid_interactions))].copy()
    evidence = rows.apply(lambda r: f"case_id={r.case_id}; interaction_id={r.interaction_id or 'blank'}", axis=1)
    return _build(rows, META["T12"], "credit_id", date_col="posting_date", amount=rows.credit_amount, evidence=evidence)


def test_missing_documentation(t: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    c = t["credits_adjustments"]
    cases = t["cases_disputes"][["case_id", "supporting_documentation_flag"]].rename(columns={"supporting_documentation_flag": "case_documentation_flag"})
    valid_interactions = set(t["interactions"].interaction_id.astype("string"))
    rows = c.merge(cases, on="case_id", how="inner")
    rows = rows[
        (rows.credit_status == "Posted")
        & rows.interaction_id.isin(valid_interactions)
        & (~_bool(rows.documentation_complete_flag) | ~_bool(rows.case_documentation_flag))
    ].copy()
    evidence = rows.apply(lambda r: f"credit_documented={int(r.documentation_complete_flag)}; case_documented={int(r.case_documentation_flag)}", axis=1)
    return _build(rows, META["T13"], "credit_id", date_col="posting_date", amount=rows.credit_amount, evidence=evidence)


def test_missing_notification(t: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    c = t["credits_adjustments"]
    valid_interactions = set(t["interactions"].interaction_id.astype("string"))
    rows = c[(c.credit_status == "Posted") & c.interaction_id.isin(valid_interactions) & ~_bool(c.customer_notified_flag)].copy()
    evidence = rows.apply(lambda r: f"interaction_id={r.interaction_id}; customer_notified_flag=0", axis=1)
    return _build(rows, META["T14"], "credit_id", date_col="posting_date", amount=rows.credit_amount, evidence=evidence)


def test_authentication_failure(t: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    c = t["credits_adjustments"]
    interactions = t["interactions"][["interaction_id", "authentication_completed_flag"]]
    rows = c.merge(interactions, on="interaction_id", how="inner")
    rows = rows[(rows.credit_status == "Posted") & ~_bool(rows.authentication_completed_flag)].copy()
    evidence = rows.apply(lambda r: f"interaction_id={r.interaction_id}; authentication_completed_flag=0", axis=1)
    return _build(rows, META["T15"], "credit_id", date_col="posting_date", amount=rows.credit_amount, evidence=evidence)


def test_manual_override(t: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    c = t["credits_adjustments"]
    rows = c[(c.credit_status == "Posted") & _bool(c.manual_override_flag) & (c.approval_status != "Approved")].copy()
    evidence = rows.apply(lambda r: f"manual_override=1; approval_status={r.approval_status}; approval_id={r.approval_id}", axis=1)
    return _build(rows, META["T16"], "credit_id", date_col="posting_date", amount=rows.credit_amount, evidence=evidence)


def test_after_hours(t: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    c = t["credits_adjustments"]
    rows = c[(c.credit_status == "Posted") & _bool(c.after_hours_flag) & ((c.approval_status != "Approved") | ~_bool(c.documentation_complete_flag))].copy()
    evidence = rows.apply(lambda r: f"after_hours=1; approval_status={r.approval_status}; documentation_complete={int(r.documentation_complete_flag)}", axis=1)
    return _build(rows, META["T17"], "credit_id", date_col="posting_date", amount=rows.credit_amount, evidence=evidence)


def test_inactive_employee(t: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    c = t["credits_adjustments"]
    agents = t["agents"][["agent_id", "employment_status"]]
    rows = c.merge(agents, on="agent_id", how="left")
    rows = rows[rows.employment_status != "Active"].copy()
    financial = np.where(rows.credit_status == "Posted", rows.credit_amount, 0.0)
    evidence = rows.apply(lambda r: f"agent_id={r.agent_id}; current_employment_status={r.employment_status}; effective termination date unavailable", axis=1)
    return _build(rows, META["T18"], "credit_id", date_col="posting_date", amount=rows.credit_amount, gross=financial, investigative=financial, evidence=evidence)


def test_self_approval(t: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    c = t["credits_adjustments"]
    approvals = t["approvals"][["approval_id", "supervisor_id"]].rename(columns={"supervisor_id": "approval_supervisor_id"})
    rows = c.merge(approvals, on="approval_id", how="left")
    rows = rows[(rows.agent_id == rows.supervisor_id) | (rows.agent_id == rows.approval_supervisor_id)].copy()
    financial = np.where(rows.credit_status == "Posted", rows.credit_amount, 0.0)
    evidence = rows.apply(lambda r: f"agent_id={r.agent_id}; credit_supervisor={r.supervisor_id}; approval_supervisor={r.approval_supervisor_id}", axis=1)
    return _build(rows, META["T19"], "credit_id", date_col="posting_date", amount=rows.credit_amount, gross=financial, investigative=financial, evidence=evidence)


def test_customer_account_mismatch(t: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    c = t["credits_adjustments"]
    accounts = t["accounts"][["account_id", "customer_id"]].rename(columns={"customer_id": "account_customer_id"})
    rows = c.merge(accounts, on="account_id", how="left")
    rows = rows[rows.customer_id != rows.account_customer_id].copy()
    financial = np.where(rows.credit_status == "Posted", rows.credit_amount, 0.0)
    evidence = rows.apply(lambda r: f"credit_customer={r.customer_id}; account_customer={r.account_customer_id}", axis=1)
    return _build(rows, META["T20"], "credit_id", date_col="posting_date", amount=rows.credit_amount, gross=financial, investigative=financial, evidence=evidence)


def test_agent_concentration(t: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    c = t["credits_adjustments"]
    interactions = t["interactions"]
    agents = t["agents"][["agent_id", "role", "team_id"]]
    posted = c[c.credit_status == "Posted"].groupby("agent_id").agg(credit_count=("credit_id", "count"), credit_amount=("credit_amount", "sum"), average_credit=("credit_amount", "mean"), maximum_credit=("credit_amount", "max")).reset_index()
    int_counts = interactions.groupby("agent_id").size().rename("interaction_count").reset_index()
    rows = agents.merge(posted, on="agent_id", how="left").merge(int_counts, on="agent_id", how="left").fillna(0)
    rows["credits_per_100_interactions"] = np.where(rows.interaction_count > 0, rows.credit_count / rows.interaction_count * 100, 0)
    rows["credit_dollars_per_interaction"] = np.where(rows.interaction_count > 0, rows.credit_amount / rows.interaction_count, 0)
    rows["rate_p90"] = rows.groupby("role").credits_per_100_interactions.transform(lambda s: s.quantile(0.90))
    rows["dollars_p90"] = rows.groupby("role").credit_dollars_per_interaction.transform(lambda s: s.quantile(0.90))
    rows = rows[(rows.credit_count >= 10) & (rows.credits_per_100_interactions >= rows.rate_p90) & (rows.credit_dollars_per_interaction >= rows.dollars_p90)].copy()
    rows["customer_id"] = ""; rows["account_id"] = ""; rows["credit_id"] = ""; rows["supervisor_id"] = ""
    evidence = rows.apply(lambda r: f"role={r.role}; credits={int(r.credit_count)}; interactions={int(r.interaction_count)}; credits_per_100={r.credits_per_100_interactions:.1f}; dollars_per_interaction={r.credit_dollars_per_interaction:.2f}", axis=1)
    return _build(rows, META["T21"], "agent_id", amount=0.0, gross=0.0, investigative=0.0, evidence=evidence)


def test_customer_concentration(t: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    c = t["credits_adjustments"]
    charges = t["charges"]
    credits = c[c.credit_status == "Posted"].groupby("customer_id").agg(credit_count=("credit_id", "count"), credit_amount=("credit_amount", "sum"), average_credit=("credit_amount", "mean")).reset_index()
    posted_charges = charges[charges.charge_status == "Posted"].groupby("customer_id").agg(charge_amount=("total_charge_amount", "sum")).reset_index()
    rows = credits.merge(posted_charges, on="customer_id", how="left").fillna({"charge_amount": 0.0})
    rows["credit_to_charge_ratio"] = np.where(rows.charge_amount > 0, rows.credit_amount / rows.charge_amount, np.nan)
    threshold = rows.credit_to_charge_ratio.quantile(0.90)
    rows = rows[(rows.credit_count >= 3) & (rows.credit_to_charge_ratio >= threshold)].copy()
    rows["account_id"] = ""; rows["agent_id"] = ""; rows["credit_id"] = ""; rows["supervisor_id"] = ""
    evidence = rows.apply(lambda r: f"credits={int(r.credit_count)}; credit_amount={r.credit_amount:.2f}; posted_charges={r.charge_amount:.2f}; ratio={r.credit_to_charge_ratio:.2f}", axis=1)
    return _build(rows, META["T22"], "customer_id", amount=0.0, gross=0.0, investigative=0.0, evidence=evidence)


def test_agent_customer_pairing(t: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    c = t["credits_adjustments"]
    rows = c[c.credit_status == "Posted"].groupby(["agent_id", "customer_id"]).agg(pair_count=("credit_id", "count"), pair_amount=("credit_amount", "sum"), account_count=("account_id", "nunique")).reset_index()
    qualifying = rows[rows.pair_count >= 3].copy()
    threshold = qualifying.pair_amount.quantile(0.95) if not qualifying.empty else np.nan
    rows = qualifying[qualifying.pair_amount >= threshold].copy() if not qualifying.empty else qualifying
    rows["record_id"] = rows.agent_id + "|" + rows.customer_id
    rows["account_id"] = ""; rows["credit_id"] = ""; rows["supervisor_id"] = ""
    evidence = rows.apply(lambda r: f"pair_count={int(r.pair_count)}; pair_amount={r.pair_amount:.2f}; distinct_accounts={int(r.account_count)}", axis=1)
    return _build(rows, META["T23"], "record_id", amount=0.0, gross=0.0, investigative=0.0, evidence=evidence)


def _promise_population(t: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    interactions = t["interactions"].copy()
    promise_actions = ["Issue credit", "Process refund", "Apply promotion"]
    interactions = interactions[interactions.promised_action.isin(promise_actions)].copy()
    posted = t["credits_adjustments"][t["credits_adjustments"].credit_status == "Posted"].groupby("interaction_id").agg(
        linked_credit_count=("credit_id", "count"),
        linked_credit_amount=("credit_amount", "sum"),
        first_credit_id=("credit_id", "first"),
        latest_posting_date=("posting_date", "max"),
    ).reset_index()
    rows = interactions.merge(posted, on="interaction_id", how="left")
    rows["linked_credit_count"] = rows.linked_credit_count.fillna(0).astype(int)
    rows["linked_credit_amount"] = rows.linked_credit_amount.fillna(0.0)
    rows["first_credit_id"] = rows.first_credit_id.fillna("")
    return rows


def test_promise_not_completed(t: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = _promise_population(t)
    rows = rows[(~_bool(rows.actual_action_completed_flag)) & (rows.linked_credit_count == 0)].copy()
    amount = pd.to_numeric(rows.promised_amount, errors="coerce").fillna(0.0)
    evidence = rows.apply(lambda r: f"promised_action={r.promised_action}; completed=0; linked_credit_count={r.linked_credit_count}; promised_amount={r.promised_amount}", axis=1)
    return _build(rows, META["T24"], "interaction_id", date_col="interaction_date", amount=amount, evidence=evidence)


def test_promise_amount_mismatch(t: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = _promise_population(t)
    rows["promised_amount_num"] = pd.to_numeric(rows.promised_amount, errors="coerce")
    rows["amount_difference"] = (rows.promised_amount_num - rows.linked_credit_amount).abs()
    rows = rows[_bool(rows.actual_action_completed_flag) & (rows.linked_credit_count > 0) & rows.promised_amount_num.notna() & (rows.amount_difference > 1.0)].copy()
    rows["credit_id"] = rows.first_credit_id
    evidence = rows.apply(lambda r: f"promised={r.promised_amount_num:.2f}; linked_posted_total={r.linked_credit_amount:.2f}; difference={r.amount_difference:.2f}", axis=1)
    return _build(rows, META["T25"], "interaction_id", date_col="interaction_date", amount=rows.linked_credit_amount, direct=rows.amount_difference, investigative=0.0, evidence=evidence)


def test_promise_late(t: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = _promise_population(t)
    rows = rows[_bool(rows.actual_action_completed_flag) & (rows.linked_credit_count > 0) & rows.promised_completion_date.notna() & (rows.latest_posting_date > rows.promised_completion_date)].copy()
    amount = pd.to_numeric(rows.promised_amount, errors="coerce").fillna(rows.linked_credit_amount)
    rows["credit_id"] = rows.first_credit_id
    evidence = rows.apply(lambda r: f"promised_due={r.promised_completion_date.date()}; latest_post={r.latest_posting_date.date()}; linked_total={r.linked_credit_amount:.2f}", axis=1)
    return _build(rows, META["T26"], "interaction_id", date_col="interaction_date", amount=amount, evidence=evidence)


def transcript_aggregate(t: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    transcripts = t["transcripts"].copy().sort_values(["transcript_id", "interaction_id", "turn_number"])
    customer = transcripts[transcripts.speaker == "Customer"].groupby("interaction_id").agg(
        customer_refund_flag=("contains_refund_request_flag", lambda s: _bool(s).any()),
        customer_dispute_flag=("contains_dispute_flag", lambda s: _bool(s).any()),
        customer_text=("utterance", lambda s: " ".join(s.astype(str))),
    ).reset_index()
    all_turns = transcripts.groupby("interaction_id").agg(
        transcript_id=("transcript_id", "first"),
        transcript_text=("utterance", lambda s: " ".join(s.astype(str))),
        contains_promise=("contains_promise_flag", lambda s: _bool(s).any()),
        contains_compliance=("contains_compliance_language_flag", lambda s: _bool(s).any()),
        contains_amount=("contains_amount_flag", lambda s: _bool(s).any()),
        case_id=("case_id", "first"),
        account_id=("account_id", "first"),
        customer_id=("customer_id", "first"),
        agent_id=("agent_id", "first"),
    ).reset_index()
    return all_turns.merge(customer, on="interaction_id", how="left").fillna({"customer_refund_flag": False, "customer_dispute_flag": False, "customer_text": ""})


def test_transcript_refund_request(t: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    aggregate = transcript_aggregate(t)
    posted = t["credits_adjustments"][t["credits_adjustments"].credit_status == "Posted"].groupby("interaction_id").agg(linked_credit_count=("credit_id", "count"), linked_credit_amount=("credit_amount", "sum")).reset_index()
    interactions = t["interactions"][["interaction_id", "interaction_date", "promised_action", "contact_reason"]]
    rows = aggregate.merge(posted, on="interaction_id", how="left").merge(interactions, on="interaction_id", how="left")
    rows["linked_credit_count"] = rows.linked_credit_count.fillna(0)
    rows["linked_credit_amount"] = rows.linked_credit_amount.fillna(0.0)
    relevant_reason = rows.contact_reason.isin(["Missing refund", "Disputed charge", "Unexpected late fee", "Payment reversal"])
    rows = rows[rows.customer_refund_flag & relevant_reason & (rows.linked_credit_count == 0)].copy()
    evidence = rows.apply(lambda r: f"contact_reason={r.contact_reason}; customer_refund_flag=1; linked_credit_count=0", axis=1)
    return _build(rows, META["T27"], "interaction_id", date_col="interaction_date", amount=0.0, gross=0.0, investigative=0.0, evidence=evidence)


def test_transcript_promise(t: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    aggregate = transcript_aggregate(t)
    interactions = t["interactions"][["interaction_id", "interaction_date", "actual_action_completed_flag", "promised_amount"]]
    rows = aggregate.merge(interactions, on="interaction_id", how="left")
    rows = rows[rows.contains_promise & ~_bool(rows.actual_action_completed_flag)].copy()
    amount = pd.to_numeric(rows.promised_amount, errors="coerce").fillna(0.0)
    evidence = rows.apply(lambda r: f"transcript_promise_flag=1; actual_action_completed_flag=0; promised_amount={r.promised_amount}", axis=1)
    return _build(rows, META["T28"], "interaction_id", date_col="interaction_date", amount=amount, evidence=evidence)


def test_transcript_authentication(t: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    aggregate = transcript_aggregate(t)
    interactions = t["interactions"][["interaction_id", "interaction_date", "authentication_completed_flag"]]
    posted = t["credits_adjustments"][t["credits_adjustments"].credit_status == "Posted"].groupby("interaction_id").agg(linked_credit_amount=("credit_amount", "sum"), linked_credit_count=("credit_id", "count")).reset_index()
    rows = aggregate.merge(interactions, on="interaction_id", how="left").merge(posted, on="interaction_id", how="inner")
    rows = rows[~_bool(rows.authentication_completed_flag) & ~rows.contains_compliance].copy()
    evidence = rows.apply(lambda r: f"authentication_completed_flag=0; transcript_compliance_language=0; linked_credit_count={int(r.linked_credit_count)}", axis=1)
    return _build(rows, META["T29"], "interaction_id", date_col="interaction_date", amount=rows.linked_credit_amount, evidence=evidence)


def test_transcript_note_contradiction(t: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    aggregate = transcript_aggregate(t)
    interactions = t["interactions"][["interaction_id", "interaction_date", "agent_notes"]]
    rows = aggregate.merge(interactions, on="interaction_id", how="left")
    note = rows.agent_notes.astype("string").str.lower()
    contradictory = note.str.contains("accepted all charges|no billing concern|accepted standard explanation", regex=True, na=False)
    rows = rows[(rows.customer_refund_flag | rows.customer_dispute_flag) & contradictory].copy()
    evidence = rows.apply(lambda r: f"transcript indicates dispute/refund; agent_notes='{r.agent_notes}'", axis=1)
    return _build(rows, META["T30"], "interaction_id", date_col="interaction_date", amount=0.0, gross=0.0, investigative=0.0, evidence=evidence)


def test_transcript_summary_contradiction(t: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    interactions = t["interactions"].copy()
    mapping = {
        "Disputed charge": "disputed charge",
        "Missing refund": "missing refund",
        "Unexpected late fee": "unexpected late fee",
        "Service interruption": "service interruption",
        "Promotion not applied": "promotion not applied",
        "Payment reversal": "payment reversal",
        "Equipment fee": "equipment fee",
        "High bill": "high bill",
        "Installation fee": "installation fee",
    }
    expected_phrase = interactions.contact_reason.map(mapping).fillna("")
    summary = interactions.summary.astype("string").str.lower()
    inconsistent = pd.Series(False, index=interactions.index)
    for index in interactions.index:
        phrase = expected_phrase.loc[index]
        inconsistent.loc[index] = bool(phrase) and phrase not in summary.loc[index]
    rows = interactions[inconsistent].copy()
    rows["expected_phrase"] = expected_phrase[inconsistent]
    evidence = rows.apply(lambda r: f"contact_reason={r.contact_reason}; expected_phrase='{r.expected_phrase}'; summary='{r.summary}'", axis=1)
    return _build(rows, META["T31"], "interaction_id", date_col="interaction_date", amount=0.0, gross=0.0, investigative=0.0, evidence=evidence)


def test_duplicate_notes(t: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    interactions = t["interactions"].copy()
    interactions["note_norm"] = interactions.agent_notes.astype("string").str.strip().str.lower()
    generic = {
        "",
        "customer accepted all charges and reported no billing concern.",
        "reviewed profile; customer accepted standard explanation. no further action.",
    }
    stats = interactions[~interactions.note_norm.isin(generic)].groupby("note_norm").agg(
        row_count=("interaction_id", "size"),
        case_count=("case_id", "nunique"),
        account_count=("account_id", "nunique"),
        agent_count=("agent_id", "nunique"),
    ).reset_index()
    duplicated_notes = set(stats[(stats.row_count > 1) & (stats.case_count > 1) & ((stats.account_count == 1) | (stats.agent_count == 1))].note_norm)
    rows = interactions[interactions.note_norm.isin(duplicated_notes)].copy()
    evidence = rows.apply(lambda r: f"exact note repeated across cases: '{r.agent_notes}'", axis=1)
    return _build(rows, META["T32"], "interaction_id", date_col="interaction_date", amount=0.0, gross=0.0, investigative=0.0, evidence=evidence)


def test_closed_disputes(t: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    cases = t["cases_disputes"]
    rows = cases[(cases.case_status == "Closed") & ((cases.resolution_code == "") | (cases.resolution_summary == ""))].copy()
    amount = pd.to_numeric(rows.disputed_amount, errors="coerce").fillna(0.0)
    evidence = rows.apply(lambda r: f"resolution_code={r.resolution_code or 'blank'}; resolution_summary={'present' if r.resolution_summary else 'blank'}", axis=1)
    return _build(rows, META["T33"], "case_id", date_col="closed_date", amount=amount, evidence=evidence)


def test_promotion_eligibility(t: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    credits = t["credits_adjustments"]
    charges = t["charges"][["charge_id", "product_service_id"]].rename(columns={"charge_id": "original_charge_id"})
    products = t["products_services"][["product_service_id", "product_category", "effective_start_date", "effective_end_date"]]
    rows = credits.merge(charges, on="original_charge_id", how="left").merge(products, on="product_service_id", how="left")
    outside = rows.effective_start_date.notna() & ((rows.credit_date < rows.effective_start_date) | (rows.effective_end_date.notna() & (rows.credit_date > rows.effective_end_date)))
    rows = rows[(rows.credit_type == "Promotional adjustment") & (rows.product_category == "Promotion") & outside].copy()
    rows["charge_id"] = rows.original_charge_id
    evidence = rows.apply(lambda r: f"credit_date={r.credit_date.date()}; promotion_start={r.effective_start_date.date()}; promotion_end={r.effective_end_date.date() if pd.notna(r.effective_end_date) else 'open'}; product={r.product_service_id}", axis=1)
    return _build(rows, META["T34"], "credit_id", date_col="posting_date", amount=rows.credit_amount, evidence=evidence)


def test_service_interruption_support(t: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    credits = t["credits_adjustments"]
    cases = t["cases_disputes"][["case_id", "dispute_category", "complaint_validated_flag", "supporting_documentation_flag"]]
    rows = credits[credits.credit_type == "Service-interruption credit"].merge(cases, on="case_id", how="inner")
    rows = rows[(rows.dispute_category != "Service interruption") | ~_bool(rows.complaint_validated_flag) | ~_bool(rows.supporting_documentation_flag)].copy()
    evidence = rows.apply(lambda r: f"dispute_category={r.dispute_category}; validated={int(r.complaint_validated_flag)}; supporting_documentation={int(r.supporting_documentation_flag)}", axis=1)
    return _build(rows, META["T35"], "credit_id", date_col="posting_date", amount=rows.credit_amount, evidence=evidence)


def test_payment_reversal_original(t: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    payments = t["payments"]
    valid = set(payments.payment_id.astype("string"))
    rows = payments[_bool(payments.reversed_flag) & (payments.original_payment_id != "") & ~payments.original_payment_id.isin(valid)].copy()
    evidence = rows.apply(lambda r: f"reversed_flag=1; invalid_original_payment_id={r.original_payment_id}", axis=1)
    return _build(rows, META["T36"], "payment_id", date_col="reversal_date", amount=rows.payment_amount, evidence=evidence)


def test_charge_reversal_original(t: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    charges = t["charges"]
    valid = set(charges.charge_id.astype("string"))
    rows = charges[_bool(charges.reversal_flag) & ((charges.original_charge_id == "") | ~charges.original_charge_id.isin(valid))].copy()
    rows["agent_id"] = rows.created_by_agent_id
    evidence = rows.apply(lambda r: f"reversal_flag=1; original_charge_id={r.original_charge_id or 'blank'}", axis=1)
    return _build(rows, META["T37"], "charge_id", date_col="posting_date", amount=rows.total_charge_amount, evidence=evidence)


def test_duplicate_charges(t: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    charges = t["charges"]
    keys = ["account_id", "product_service_id", "total_charge_amount", "posting_date", "charge_type"]
    posted = charges[charges.charge_status == "Posted"].sort_values(keys + ["charge_id"]).copy()
    posted["duplicate_rank"] = posted.groupby(keys, dropna=False).cumcount()
    rows = posted[posted.duplicate_rank > 0].copy()
    rows["agent_id"] = rows.created_by_agent_id
    evidence = rows.apply(lambda r: f"duplicate group: account={r.account_id}; product={r.product_service_id}; amount={r.total_charge_amount:.2f}; date={r.posting_date.date()}; type={r.charge_type}", axis=1)
    return _build(rows, META["T38"], "charge_id", date_col="posting_date", amount=rows.total_charge_amount, direct=rows.total_charge_amount, investigative=0.0, evidence=evidence)


def test_account_reconciliation(t: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    reconciliation = t["account_reconciliations"]
    rows = reconciliation[reconciliation.reconciliation_difference.abs() > 0.01].copy()
    amount = rows.reconciliation_difference.abs()
    evidence = rows.apply(lambda r: f"expected={r.expected_closing_balance:.2f}; recorded={r.recorded_closing_balance:.2f}; difference={r.reconciliation_difference:.2f}", axis=1)
    return _build(rows, META["T39"], "account_id", amount=amount, direct=amount, investigative=0.0, evidence=evidence)


def test_negative_impossible_balances(t: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    accounts = t["accounts"]
    rows = accounts[(accounts.current_balance < -500) | (accounts.past_due_balance > accounts.current_balance.abs() + 1000)].copy()
    evidence = rows.apply(lambda r: f"current_balance={r.current_balance:.2f}; past_due_balance={r.past_due_balance:.2f}", axis=1)
    return _build(rows, META["T40"], "account_id", amount=0.0, gross=0.0, investigative=0.0, evidence=evidence)


TEST_FUNCTIONS: list[Callable[[Dict[str, pd.DataFrame]], pd.DataFrame]] = [
    test_credit_authority,
    test_missing_approval,
    test_approval_after_posting,
    test_amount_mismatch,
    test_credit_exceeds_charge,
    test_exact_duplicate_credits,
    test_near_duplicate_credits,
    test_split_credits,
    test_invalid_reason_codes,
    test_reason_type_mismatch,
    test_missing_case,
    test_missing_interaction,
    test_missing_documentation,
    test_missing_notification,
    test_authentication_failure,
    test_manual_override,
    test_after_hours,
    test_inactive_employee,
    test_self_approval,
    test_customer_account_mismatch,
    test_agent_concentration,
    test_customer_concentration,
    test_agent_customer_pairing,
    test_promise_not_completed,
    test_promise_amount_mismatch,
    test_promise_late,
    test_transcript_refund_request,
    test_transcript_promise,
    test_transcript_authentication,
    test_transcript_note_contradiction,
    test_transcript_summary_contradiction,
    test_duplicate_notes,
    test_closed_disputes,
    test_promotion_eligibility,
    test_service_interruption_support,
    test_payment_reversal_original,
    test_charge_reversal_original,
    test_duplicate_charges,
    test_account_reconciliation,
    test_negative_impossible_balances,
]


def run_all_tests(tables: Dict[str, pd.DataFrame]) -> tuple[pd.DataFrame, pd.DataFrame]:
    frames: list[pd.DataFrame] = []
    summary: list[dict[str, object]] = []
    for function in TEST_FUNCTIONS:
        result = function(tables)
        test_id = function.__name__
        if not result.empty:
            test_id = str(result.test_id.iloc[0])
        else:
            # Function order is identical to T01-T40.
            test_id = f"T{len(summary) + 1:02d}"
        meta = META[test_id]
        frames.append(result)
        summary.append(
            {
                "test_id": test_id,
                "test_name": meta.test_name,
                "exception_class": meta.exception_class,
                "severity": meta.severity,
                "confidence": meta.confidence,
                "rows": len(result),
                "gross_flagged_amount": round(float(pd.to_numeric(result.get("gross_flagged_amount", pd.Series(dtype=float)), errors="coerce").fillna(0).sum()), 2),
                "direct_measurable_amount": round(float(pd.to_numeric(result.get("direct_measurable_amount", pd.Series(dtype=float)), errors="coerce").fillna(0).sum()), 2),
                "investigative_amount": round(float(pd.to_numeric(result.get("investigative_amount", pd.Series(dtype=float)), errors="coerce").fillna(0).sum()), 2),
            }
        )
    nonempty_frames = [frame for frame in frames if not frame.empty]
    exceptions = pd.concat(nonempty_frames, ignore_index=True) if nonempty_frames else pd.DataFrame(columns=EXCEPTION_COLUMNS)
    exceptions = _add_exception_ids(exceptions)
    return exceptions, pd.DataFrame(summary)


def create_data_quality_exceptions(tables: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows: list[pd.DataFrame] = []
    interactions = tables["interactions"]
    customers = tables["customers"]

    dq1 = interactions[interactions.interaction_end_time.astype("string").eq("")].copy()
    dq1["test_id"] = "DQ01"; dq1["record_type"] = "Interaction"; dq1["record_id"] = dq1.interaction_id
    dq1["exception_category"] = "DATA_QUALITY_MISSING_END_TIME"; dq1["evidence"] = "interaction_end_time is blank"
    rows.append(dq1[["test_id", "record_type", "record_id", "customer_id", "account_id", "agent_id", "case_id", "interaction_id", "exception_category", "evidence"]])

    dq2 = interactions[interactions.agent_notes.astype("string").str.strip().eq("")].copy()
    dq2["test_id"] = "DQ02"; dq2["record_type"] = "Interaction"; dq2["record_id"] = dq2.interaction_id
    dq2["exception_category"] = "DATA_QUALITY_MISSING_AGENT_NOTES"; dq2["evidence"] = "agent_notes is blank"
    rows.append(dq2[["test_id", "record_type", "record_id", "customer_id", "account_id", "agent_id", "case_id", "interaction_id", "exception_category", "evidence"]])

    dq3 = customers[customers.city.astype("string") != customers.city.astype("string").str.title()].copy()
    dq3["test_id"] = "DQ03"; dq3["record_type"] = "Customer"; dq3["record_id"] = dq3.customer_id
    dq3["account_id"] = ""; dq3["agent_id"] = ""; dq3["case_id"] = ""; dq3["interaction_id"] = ""
    dq3["exception_category"] = "DATA_QUALITY_INCONSISTENT_CAPITALIZATION"; dq3["evidence"] = "city is not proper case: " + dq3.city.astype("string")
    rows.append(dq3[["test_id", "record_type", "record_id", "customer_id", "account_id", "agent_id", "case_id", "interaction_id", "exception_category", "evidence"]])

    result = pd.concat(rows, ignore_index=True)
    result.insert(0, "exception_id", [f"DQ-{index + 1:05d}" for index in range(len(result))])
    result["control_id"] = "DATA_QUALITY"
    result["severity"] = "Low"
    result["confidence"] = "High"
    return result


def calculate_exposure(exceptions: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    data = exceptions.copy()
    gross = round(float(pd.to_numeric(data.gross_flagged_amount, errors="coerce").fillna(0).sum()), 2)

    def dedup_key(row: pd.Series) -> str:
        for column in ["credit_id", "payment_id", "charge_id", "case_id", "interaction_id", "account_id", "record_id"]:
            value = str(row.get(column, ""))
            if value and value.lower() != "nan":
                return f"{column}:{value}"
        return f"row:{row.name}"

    data["dedup_key"] = data.apply(dedup_key, axis=1)
    deduplicated = data.sort_values(["dedup_key", "gross_flagged_amount"], ascending=[True, False]).drop_duplicates("dedup_key")
    direct = data[data.direct_measurable_amount > 0].sort_values(["dedup_key", "direct_measurable_amount"], ascending=[True, False]).drop_duplicates("dedup_key")
    investigative = data[data.investigative_amount > 0].sort_values(["dedup_key", "investigative_amount"], ascending=[True, False]).drop_duplicates("dedup_key")
    dedup_amount = round(float(deduplicated.gross_flagged_amount.sum()), 2)
    direct_amount = round(float(direct.direct_measurable_amount.sum()), 2)
    investigative_amount = round(float(investigative.investigative_amount.sum()), 2)
    bridge = pd.DataFrame(
        [
            {"exposure_class": "Gross overlapping flagged amount", "amount": gross, "definition": "Sum of all exception-row flagged amounts before overlap removal."},
            {"exposure_class": "Overlap removed", "amount": round(gross - dedup_amount, 2), "definition": "Repeated underlying-record amounts removed using the documented record hierarchy."},
            {"exposure_class": "Record-level deduplicated flagged amount", "amount": dedup_amount, "definition": "Largest flagged amount per underlying record; not confirmed loss."},
            {"exposure_class": "Direct measurable amount", "amount": direct_amount, "definition": "Calculable differences only, deduplicated by underlying record."},
            {"exposure_class": "Investigative amount", "amount": investigative_amount, "definition": "Transaction value requiring review but not measurable as loss."},
            {"exposure_class": "Confirmed loss", "amount": 0.0, "definition": "Confirmed financial loss was not established."},
        ]
    )
    return bridge, deduplicated, direct, investigative
