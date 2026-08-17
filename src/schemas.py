from __future__ import annotations

IDENTIFIER_COLUMNS = [
    "customer_id", "account_id", "agent_id", "supervisor_id", "charge_id", "credit_id",
    "payment_id", "case_id", "interaction_id", "transcript_id", "approval_id", "invoice_id",
    "location_id", "product_service_id", "reason_code", "control_id", "original_charge_id",
    "original_payment_id", "assigned_agent_id", "assigned_supervisor_id", "disputed_charge_id",
    "created_by_agent_id", "service_plan_id", "reference_number", "related_record_id",
]

MONETARY_COLUMNS = [
    "credit_amount", "requested_amount", "approved_amount", "agent_authority_limit", "charge_amount",
    "tax_amount", "total_charge_amount", "payment_amount", "disputed_amount", "opening_balance",
    "current_balance", "past_due_balance", "credit_limit_or_adjustment_limit", "approval_threshold",
    "monthly_price", "one_time_price", "total_charges", "total_credits", "total_payments",
    "payment_reversals", "expected_closing_balance", "recorded_closing_balance", "reconciliation_difference",
    "promised_amount", "approval_limit", "account_risk_score", "quality_score",
]

INTEGER_COLUMNS = [
    "billing_cycle_day", "tenure_months", "interaction_duration_seconds", "transfer_count",
    "hold_time_seconds", "turn_number", "timestamp_seconds", "customer_satisfaction_score",
]

BOOLEAN_COLUMNS = [
    "autopay_flag", "paperless_billing_flag", "taxable_flag", "active_flag", "reversal_flag",
    "approval_required_flag", "documentation_complete_flag", "customer_notified_flag",
    "manual_override_flag", "after_hours_flag", "policy_exception_flag", "reversed_flag",
    "remote_flag", "training_completed_flag", "escalated_flag", "complaint_validated_flag",
    "supporting_documentation_flag", "regulatory_complaint_flag", "first_contact_resolution_flag",
    "authentication_completed_flag", "actual_action_completed_flag", "override_flag",
    "approval_within_limit_flag", "contains_amount_flag", "contains_promise_flag",
    "contains_dispute_flag", "contains_refund_request_flag", "contains_compliance_language_flag",
    "marketing_opt_in", "vulnerability_indicator", "synthetic_identity_flag",
    "documentation_required_flag", "supervisor_approval_required_flag", "seeded_flag",
]

DATE_COLUMNS = [
    "customer_since_date", "account_open_date", "account_close_date", "effective_start_date",
    "effective_end_date", "charge_date", "posting_date", "billing_period_start", "billing_period_end",
    "credit_date", "payment_date", "reversal_date", "hire_date", "opened_date", "closed_date",
    "interaction_date", "promised_completion_date", "approval_requested_date", "approval_decision_date",
    "open_date",
]

PRIMARY_KEYS = {
    "customers": "customer_id",
    "accounts": "account_id",
    "products_services": "product_service_id",
    "charges": "charge_id",
    "credits_adjustments": "credit_id",
    "payments": "payment_id",
    "agents": "agent_id",
    "supervisors": "supervisor_id",
    "cases_disputes": "case_id",
    "interactions": "interaction_id",
    "approvals": "approval_id",
    "locations": "location_id",
    "reason_codes": "reason_code",
    "control_rules": "control_id",
    "account_reconciliations": "account_id",
}

SOURCE_TABLES = [
    "customers", "accounts", "products_services", "charges", "credits_adjustments", "payments",
    "agents", "supervisors", "cases_disputes", "interactions", "transcripts", "approvals",
    "locations", "reason_codes", "control_rules", "account_reconciliations",
]
