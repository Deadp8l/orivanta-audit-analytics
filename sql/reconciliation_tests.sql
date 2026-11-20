-- reconciliation_tests.sql
-- SQLite. Each query returns the records that one audit test flags, in a standard set of columns.
-- T21-T23 are Python-only (percentile-based behavioral indicators), so they have no SQL here.

-- T39: Account reconciliation difference
-- Flags: Absolute reconciliation difference exceeds $0.01.
SELECT 'T39' AS test_id,
    record_id AS record_id,
    COALESCE(account_id, '') AS account_id,
    COALESCE(customer_id, '') AS customer_id,
    COALESCE(agent_id, '') AS agent_id,
    CAST(amount AS REAL) AS transaction_amount,
    CAST(gross_amount AS REAL) AS gross_flagged_amount,
    CAST(direct_amount AS REAL) AS direct_measurable_amount
FROM (
    SELECT account_id record_id,
        account_id,
        customer_id,
        '' agent_id,
        ABS(reconciliation_difference) amount,
        ABS(reconciliation_difference) gross_amount,
        ABS(reconciliation_difference) direct_amount
    FROM account_reconciliations
    WHERE ABS(reconciliation_difference)>0.01
) q;

-- T40: Negative or impossible balance condition
-- Flags: Current balance is below -$500 or past-due balance exceeds absolute current balance by more than $1,000.
SELECT 'T40' AS test_id,
    record_id AS record_id,
    COALESCE(account_id, '') AS account_id,
    COALESCE(customer_id, '') AS customer_id,
    COALESCE(agent_id, '') AS agent_id,
    CAST(amount AS REAL) AS transaction_amount,
    CAST(gross_amount AS REAL) AS gross_flagged_amount,
    CAST(direct_amount AS REAL) AS direct_measurable_amount
FROM (
    SELECT account_id record_id,
        account_id,
        customer_id,
        '' agent_id,
        0 amount,
        0 gross_amount,
        0 direct_amount
    FROM accounts
    WHERE current_balance < -500
        OR past_due_balance > ABS(current_balance)+1000
) q;
