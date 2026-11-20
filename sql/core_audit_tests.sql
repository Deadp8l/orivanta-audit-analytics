-- core_audit_tests.sql
-- SQLite. Each query returns the records that one audit test flags, in a standard set of columns.
-- T21-T23 are Python-only (percentile-based behavioral indicators), so they have no SQL here.

-- T01: Credits above authority without approval
-- Flags: Posted credit amount exceeds authority and approval status is not Approved.
SELECT 'T01' AS test_id,
    record_id AS record_id,
    COALESCE(account_id, '') AS account_id,
    COALESCE(customer_id, '') AS customer_id,
    COALESCE(agent_id, '') AS agent_id,
    CAST(amount AS REAL) AS transaction_amount,
    CAST(gross_amount AS REAL) AS gross_flagged_amount,
    CAST(direct_amount AS REAL) AS direct_measurable_amount
FROM (
    SELECT credit_id record_id,
        account_id,
        customer_id,
        agent_id,
        credit_amount amount,
        ABS(credit_amount) gross_amount,
        0 direct_amount
    FROM credits_adjustments
    WHERE credit_status='Posted'
        AND CAST(credit_amount AS REAL)>CAST(agent_authority_limit AS REAL)
        AND approval_status<>'Approved'
) q;

-- T02: Missing required approval
-- Flags: Posted credit requires approval and has no approval ID or a nonapproved status.
SELECT 'T02' AS test_id,
    record_id AS record_id,
    COALESCE(account_id, '') AS account_id,
    COALESCE(customer_id, '') AS customer_id,
    COALESCE(agent_id, '') AS agent_id,
    CAST(amount AS REAL) AS transaction_amount,
    CAST(gross_amount AS REAL) AS gross_flagged_amount,
    CAST(direct_amount AS REAL) AS direct_measurable_amount
FROM (
    SELECT credit_id record_id,
        account_id,
        customer_id,
        agent_id,
        credit_amount amount,
        ABS(credit_amount) gross_amount,
        0 direct_amount
    FROM credits_adjustments
    WHERE credit_status='Posted'
        AND CAST(approval_required_flag AS INTEGER)=1
        AND (COALESCE(approval_id, '')='' OR approval_status IN ('Missing', 'Denied', 'Pending'))
) q;

-- T05: Credit exceeds original charge
-- Flags: Posted credit amount exceeds the linked charge total.
SELECT 'T05' AS test_id,
    record_id AS record_id,
    COALESCE(account_id, '') AS account_id,
    COALESCE(customer_id, '') AS customer_id,
    COALESCE(agent_id, '') AS agent_id,
    CAST(amount AS REAL) AS transaction_amount,
    CAST(gross_amount AS REAL) AS gross_flagged_amount,
    CAST(direct_amount AS REAL) AS direct_measurable_amount
FROM (
    SELECT c.credit_id record_id,
        c.account_id,
        c.customer_id,
        c.agent_id,
        c.credit_amount amount,
        ABS(c.credit_amount) gross_amount,
        ABS(c.credit_amount-ch.total_charge_amount) direct_amount
    FROM credits_adjustments c
    JOIN charges ch ON c.original_charge_id=ch.charge_id
    WHERE c.credit_status='Posted'
        AND c.credit_amount>ch.total_charge_amount
) q;

-- T03: Approval decision after posting
-- Flags: Approved decision date is more than one calendar day after the posting date; one-day cases are excluded because posting is date-only.
SELECT 'T03' AS test_id,
    record_id AS record_id,
    COALESCE(account_id, '') AS account_id,
    COALESCE(customer_id, '') AS customer_id,
    COALESCE(agent_id, '') AS agent_id,
    CAST(amount AS REAL) AS transaction_amount,
    CAST(gross_amount AS REAL) AS gross_flagged_amount,
    CAST(direct_amount AS REAL) AS direct_measurable_amount
FROM (
    SELECT c.credit_id record_id,
        c.account_id,
        c.customer_id,
        c.agent_id,
        c.credit_amount amount,
        ABS(c.credit_amount) gross_amount,
        0 direct_amount
    FROM credits_adjustments c
    JOIN approvals a ON c.approval_id=a.approval_id
    WHERE c.credit_status='Posted'
        AND a.approval_status='Approved'
        AND julianday(date(a.approval_decision_date))-julianday(date(c.posting_date))>1
) q;

-- T04: Approved versus posted amount mismatch
-- Flags: Posted amount differs from either the credit record approved amount or the linked approval approved amount by more than $0.01.
SELECT 'T04' AS test_id,
    record_id AS record_id,
    COALESCE(account_id, '') AS account_id,
    COALESCE(customer_id, '') AS customer_id,
    COALESCE(agent_id, '') AS agent_id,
    CAST(amount AS REAL) AS transaction_amount,
    CAST(gross_amount AS REAL) AS gross_flagged_amount,
    CAST(direct_amount AS REAL) AS direct_measurable_amount
FROM (
    SELECT c.credit_id record_id,
        c.account_id,
        c.customer_id,
        c.agent_id,
        c.credit_amount amount,
        ABS(c.credit_amount) gross_amount,
        MAX(ABS(c.credit_amount-c.approved_amount), ABS(c.credit_amount-a.approved_amount)) direct_amount
    FROM credits_adjustments c
    LEFT JOIN approvals a ON c.approval_id=a.approval_id
    WHERE c.credit_status='Posted'
        AND c.approval_status='Approved'
        AND (ABS(c.credit_amount-c.approved_amount)>0.01 OR ABS(c.credit_amount-a.approved_amount)>0.01)
) q;

-- T09: Invalid or inactive reason code
-- Flags: Reason code is missing from the reason-code table or is inactive.
SELECT 'T09' AS test_id,
    record_id AS record_id,
    COALESCE(account_id, '') AS account_id,
    COALESCE(customer_id, '') AS customer_id,
    COALESCE(agent_id, '') AS agent_id,
    CAST(amount AS REAL) AS transaction_amount,
    CAST(gross_amount AS REAL) AS gross_flagged_amount,
    CAST(direct_amount AS REAL) AS direct_measurable_amount
FROM (
    SELECT c.credit_id record_id,
        c.account_id,
        c.customer_id,
        c.agent_id,
        c.credit_amount amount,
        CASE WHEN c.credit_status='Posted' THEN ABS(c.credit_amount) ELSE 0 END gross_amount,
        0 direct_amount
    FROM credits_adjustments c
    LEFT JOIN reason_codes r ON c.reason_code=r.reason_code
    WHERE r.reason_code IS NULL
        OR CAST(COALESCE(r.active_flag, 0) AS INTEGER)<>1
) q;

-- T10: Reason code and credit type mismatch
-- Flags: Credit type differs from the type assigned to the reason code.
SELECT 'T10' AS test_id,
    record_id AS record_id,
    COALESCE(account_id, '') AS account_id,
    COALESCE(customer_id, '') AS customer_id,
    COALESCE(agent_id, '') AS agent_id,
    CAST(amount AS REAL) AS transaction_amount,
    CAST(gross_amount AS REAL) AS gross_flagged_amount,
    CAST(direct_amount AS REAL) AS direct_measurable_amount
FROM (
    SELECT c.credit_id record_id,
        c.account_id,
        c.customer_id,
        c.agent_id,
        c.credit_amount amount,
        ABS(c.credit_amount) gross_amount,
        0 direct_amount
    FROM credits_adjustments c
    JOIN reason_codes r ON c.reason_code=r.reason_code
    WHERE c.credit_status='Posted'
        AND c.credit_type<>r.credit_type
) q;

-- T11: Missing case support
-- Flags: Posted credit has an interaction but no valid case reference.
SELECT 'T11' AS test_id,
    record_id AS record_id,
    COALESCE(account_id, '') AS account_id,
    COALESCE(customer_id, '') AS customer_id,
    COALESCE(agent_id, '') AS agent_id,
    CAST(amount AS REAL) AS transaction_amount,
    CAST(gross_amount AS REAL) AS gross_flagged_amount,
    CAST(direct_amount AS REAL) AS direct_measurable_amount
FROM (
    SELECT c.credit_id record_id,
        c.account_id,
        c.customer_id,
        c.agent_id,
        c.credit_amount amount,
        ABS(c.credit_amount) gross_amount,
        0 direct_amount
    FROM credits_adjustments c
    LEFT JOIN cases_disputes ca ON c.case_id=ca.case_id
    WHERE c.credit_status='Posted'
        AND COALESCE(c.interaction_id, '')<>''
        AND (COALESCE(c.case_id, '')='' OR ca.case_id IS NULL)
) q;

-- T12: Missing interaction support
-- Flags: Posted credit has a case but no valid interaction reference.
SELECT 'T12' AS test_id,
    record_id AS record_id,
    COALESCE(account_id, '') AS account_id,
    COALESCE(customer_id, '') AS customer_id,
    COALESCE(agent_id, '') AS agent_id,
    CAST(amount AS REAL) AS transaction_amount,
    CAST(gross_amount AS REAL) AS gross_flagged_amount,
    CAST(direct_amount AS REAL) AS direct_measurable_amount
FROM (
    SELECT c.credit_id record_id,
        c.account_id,
        c.customer_id,
        c.agent_id,
        c.credit_amount amount,
        ABS(c.credit_amount) gross_amount,
        0 direct_amount
    FROM credits_adjustments c
    LEFT JOIN interactions i ON c.interaction_id=i.interaction_id
    WHERE c.credit_status='Posted'
        AND COALESCE(c.case_id, '')<>''
        AND (COALESCE(c.interaction_id, '')='' OR i.interaction_id IS NULL)
) q;

-- T13: Missing required documentation
-- Flags: Posted credit with valid case and interaction has incomplete credit or case documentation.
SELECT 'T13' AS test_id,
    record_id AS record_id,
    COALESCE(account_id, '') AS account_id,
    COALESCE(customer_id, '') AS customer_id,
    COALESCE(agent_id, '') AS agent_id,
    CAST(amount AS REAL) AS transaction_amount,
    CAST(gross_amount AS REAL) AS gross_flagged_amount,
    CAST(direct_amount AS REAL) AS direct_measurable_amount
FROM (
    SELECT c.credit_id record_id,
        c.account_id,
        c.customer_id,
        c.agent_id,
        c.credit_amount amount,
        ABS(c.credit_amount) gross_amount,
        0 direct_amount
    FROM credits_adjustments c
    JOIN cases_disputes ca ON c.case_id=ca.case_id
    JOIN interactions i ON c.interaction_id=i.interaction_id
    WHERE c.credit_status='Posted'
        AND (CAST(c.documentation_complete_flag AS INTEGER)<>1 OR CAST(ca.supporting_documentation_flag AS INTEGER)<>1)
) q;

-- T14: Posted credit not communicated
-- Flags: Posted credit has a linked interaction and customer-notified flag is false.
SELECT 'T14' AS test_id,
    record_id AS record_id,
    COALESCE(account_id, '') AS account_id,
    COALESCE(customer_id, '') AS customer_id,
    COALESCE(agent_id, '') AS agent_id,
    CAST(amount AS REAL) AS transaction_amount,
    CAST(gross_amount AS REAL) AS gross_flagged_amount,
    CAST(direct_amount AS REAL) AS direct_measurable_amount
FROM (
    SELECT c.credit_id record_id,
        c.account_id,
        c.customer_id,
        c.agent_id,
        c.credit_amount amount,
        ABS(c.credit_amount) gross_amount,
        0 direct_amount
    FROM credits_adjustments c
    JOIN interactions i ON c.interaction_id=i.interaction_id
    WHERE c.credit_status='Posted'
        AND CAST(c.customer_notified_flag AS INTEGER)<>1
) q;

-- T15: Authentication failure
-- Flags: Posted credit has a linked interaction with authentication-completed flag false.
SELECT 'T15' AS test_id,
    record_id AS record_id,
    COALESCE(account_id, '') AS account_id,
    COALESCE(customer_id, '') AS customer_id,
    COALESCE(agent_id, '') AS agent_id,
    CAST(amount AS REAL) AS transaction_amount,
    CAST(gross_amount AS REAL) AS gross_flagged_amount,
    CAST(direct_amount AS REAL) AS direct_measurable_amount
FROM (
    SELECT c.credit_id record_id,
        c.account_id,
        c.customer_id,
        c.agent_id,
        c.credit_amount amount,
        ABS(c.credit_amount) gross_amount,
        0 direct_amount
    FROM credits_adjustments c
    JOIN interactions i ON c.interaction_id=i.interaction_id
    WHERE c.credit_status='Posted'
        AND CAST(i.authentication_completed_flag AS INTEGER)<>1
) q;

-- T16: Manual override without approval
-- Flags: Posted manual override has approval status other than Approved.
SELECT 'T16' AS test_id,
    record_id AS record_id,
    COALESCE(account_id, '') AS account_id,
    COALESCE(customer_id, '') AS customer_id,
    COALESCE(agent_id, '') AS agent_id,
    CAST(amount AS REAL) AS transaction_amount,
    CAST(gross_amount AS REAL) AS gross_flagged_amount,
    CAST(direct_amount AS REAL) AS direct_measurable_amount
FROM (
    SELECT credit_id record_id,
        account_id,
        customer_id,
        agent_id,
        credit_amount amount,
        ABS(credit_amount) gross_amount,
        0 direct_amount
    FROM credits_adjustments
    WHERE credit_status='Posted'
        AND CAST(manual_override_flag AS INTEGER)=1
        AND approval_status<>'Approved'
) q;

-- T17: After-hours credit without review
-- Flags: Posted after-hours credit lacks approved status or complete documentation.
SELECT 'T17' AS test_id,
    record_id AS record_id,
    COALESCE(account_id, '') AS account_id,
    COALESCE(customer_id, '') AS customer_id,
    COALESCE(agent_id, '') AS agent_id,
    CAST(amount AS REAL) AS transaction_amount,
    CAST(gross_amount AS REAL) AS gross_flagged_amount,
    CAST(direct_amount AS REAL) AS direct_measurable_amount
FROM (
    SELECT credit_id record_id,
        account_id,
        customer_id,
        agent_id,
        credit_amount amount,
        ABS(credit_amount) gross_amount,
        0 direct_amount
    FROM credits_adjustments
    WHERE credit_status='Posted'
        AND CAST(after_hours_flag AS INTEGER)=1
        AND (approval_status<>'Approved' OR CAST(documentation_complete_flag AS INTEGER)<>1)
) q;

-- T18: Inactive employee activity
-- Flags: Credit was processed by an employee currently marked inactive; termination effective date is unavailable.
SELECT 'T18' AS test_id,
    record_id AS record_id,
    COALESCE(account_id, '') AS account_id,
    COALESCE(customer_id, '') AS customer_id,
    COALESCE(agent_id, '') AS agent_id,
    CAST(amount AS REAL) AS transaction_amount,
    CAST(gross_amount AS REAL) AS gross_flagged_amount,
    CAST(direct_amount AS REAL) AS direct_measurable_amount
FROM (
    SELECT c.credit_id record_id,
        c.account_id,
        c.customer_id,
        c.agent_id,
        c.credit_amount amount,
        CASE WHEN c.credit_status='Posted' THEN ABS(c.credit_amount) ELSE 0 END gross_amount,
        0 direct_amount
    FROM credits_adjustments c
    LEFT JOIN agents a ON c.agent_id=a.agent_id
    WHERE COALESCE(a.employment_status, '')<>'Active'
) q;

-- T19: Self-approval
-- Flags: Credit agent ID equals supervisor ID or linked approval supervisor ID.
SELECT 'T19' AS test_id,
    record_id AS record_id,
    COALESCE(account_id, '') AS account_id,
    COALESCE(customer_id, '') AS customer_id,
    COALESCE(agent_id, '') AS agent_id,
    CAST(amount AS REAL) AS transaction_amount,
    CAST(gross_amount AS REAL) AS gross_flagged_amount,
    CAST(direct_amount AS REAL) AS direct_measurable_amount
FROM (
    SELECT c.credit_id record_id,
        c.account_id,
        c.customer_id,
        c.agent_id,
        c.credit_amount amount,
        CASE WHEN c.credit_status='Posted' THEN ABS(c.credit_amount) ELSE 0 END gross_amount,
        0 direct_amount
    FROM credits_adjustments c
    LEFT JOIN approvals a ON c.approval_id=a.approval_id
    WHERE c.agent_id=c.supervisor_id
        OR c.agent_id=a.supervisor_id
) q;

-- T20: Customer-account mismatch
-- Flags: Credit customer ID differs from account customer ID.
SELECT 'T20' AS test_id,
    record_id AS record_id,
    COALESCE(account_id, '') AS account_id,
    COALESCE(customer_id, '') AS customer_id,
    COALESCE(agent_id, '') AS agent_id,
    CAST(amount AS REAL) AS transaction_amount,
    CAST(gross_amount AS REAL) AS gross_flagged_amount,
    CAST(direct_amount AS REAL) AS direct_measurable_amount
FROM (
    SELECT c.credit_id record_id,
        c.account_id,
        c.customer_id,
        c.agent_id,
        c.credit_amount amount,
        CASE WHEN c.credit_status='Posted' THEN ABS(c.credit_amount) ELSE 0 END gross_amount,
        0 direct_amount
    FROM credits_adjustments c
    JOIN accounts ac ON c.account_id=ac.account_id
    WHERE c.customer_id<>ac.customer_id
) q;

-- T33: Closed case without resolution evidence
-- Flags: Closed case has blank resolution code or resolution summary.
SELECT 'T33' AS test_id,
    record_id AS record_id,
    COALESCE(account_id, '') AS account_id,
    COALESCE(customer_id, '') AS customer_id,
    COALESCE(agent_id, '') AS agent_id,
    CAST(amount AS REAL) AS transaction_amount,
    CAST(gross_amount AS REAL) AS gross_flagged_amount,
    CAST(direct_amount AS REAL) AS direct_measurable_amount
FROM (
    SELECT case_id record_id,
        account_id,
        customer_id,
        assigned_agent_id agent_id,
        COALESCE(disputed_amount, 0) amount,
        ABS(COALESCE(disputed_amount, 0)) gross_amount,
        0 direct_amount
    FROM cases_disputes
    WHERE case_status='Closed'
        AND (COALESCE(resolution_code, '')='' OR COALESCE(resolution_summary, '')='')
) q;
