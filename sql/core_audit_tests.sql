-- core_audit_tests.sql
-- Recruiter-facing consolidated SQL derived from validated source files.


-- ===== Source file: 02_credit_authorization_tests.sql =====

-- SQLite-compatible audit queries. Each statement returns a standardized record-level population.
-- T21-T23 remain Python-primary normalized behavioral indicators.

SELECT 'T01' AS test_id, record_id AS record_id, COALESCE(account_id,'') AS account_id, COALESCE(customer_id,'') AS customer_id, COALESCE(agent_id,'') AS agent_id, CAST(amount AS REAL) AS transaction_amount, CAST(gross_amount AS REAL) AS gross_flagged_amount, CAST(direct_amount AS REAL) AS direct_measurable_amount FROM (SELECT credit_id record_id, account_id, customer_id, agent_id, credit_amount amount, ABS(credit_amount) gross_amount, 0 direct_amount FROM credits_adjustments WHERE credit_status='Posted' AND CAST(credit_amount AS REAL)>CAST(agent_authority_limit AS REAL) AND approval_status<>'Approved') q;

SELECT 'T02' AS test_id, record_id AS record_id, COALESCE(account_id,'') AS account_id, COALESCE(customer_id,'') AS customer_id, COALESCE(agent_id,'') AS agent_id, CAST(amount AS REAL) AS transaction_amount, CAST(gross_amount AS REAL) AS gross_flagged_amount, CAST(direct_amount AS REAL) AS direct_measurable_amount FROM (SELECT credit_id record_id, account_id, customer_id, agent_id, credit_amount amount, ABS(credit_amount) gross_amount, 0 direct_amount FROM credits_adjustments WHERE credit_status='Posted' AND CAST(approval_required_flag AS INTEGER)=1 AND (COALESCE(approval_id,'')='' OR approval_status IN ('Missing','Denied','Pending'))) q;

SELECT 'T05' AS test_id, record_id AS record_id, COALESCE(account_id,'') AS account_id, COALESCE(customer_id,'') AS customer_id, COALESCE(agent_id,'') AS agent_id, CAST(amount AS REAL) AS transaction_amount, CAST(gross_amount AS REAL) AS gross_flagged_amount, CAST(direct_amount AS REAL) AS direct_measurable_amount FROM (SELECT c.credit_id record_id,c.account_id,c.customer_id,c.agent_id,c.credit_amount amount,ABS(c.credit_amount) gross_amount,ABS(c.credit_amount-ch.total_charge_amount) direct_amount FROM credits_adjustments c JOIN charges ch ON c.original_charge_id=ch.charge_id WHERE c.credit_status='Posted' AND c.credit_amount>ch.total_charge_amount) q;


-- ===== Source file: 03_approval_tests.sql =====

-- SQLite-compatible audit queries. Each statement returns a standardized record-level population.
-- T21-T23 remain Python-primary normalized behavioral indicators.

SELECT 'T03' AS test_id, record_id AS record_id, COALESCE(account_id,'') AS account_id, COALESCE(customer_id,'') AS customer_id, COALESCE(agent_id,'') AS agent_id, CAST(amount AS REAL) AS transaction_amount, CAST(gross_amount AS REAL) AS gross_flagged_amount, CAST(direct_amount AS REAL) AS direct_measurable_amount FROM (SELECT c.credit_id record_id,c.account_id,c.customer_id,c.agent_id,c.credit_amount amount,ABS(c.credit_amount) gross_amount,0 direct_amount FROM credits_adjustments c JOIN approvals a ON c.approval_id=a.approval_id WHERE c.credit_status='Posted' AND a.approval_status='Approved' AND julianday(date(a.approval_decision_date))-julianday(date(c.posting_date))>1) q;

SELECT 'T04' AS test_id, record_id AS record_id, COALESCE(account_id,'') AS account_id, COALESCE(customer_id,'') AS customer_id, COALESCE(agent_id,'') AS agent_id, CAST(amount AS REAL) AS transaction_amount, CAST(gross_amount AS REAL) AS gross_flagged_amount, CAST(direct_amount AS REAL) AS direct_measurable_amount FROM (SELECT c.credit_id record_id,c.account_id,c.customer_id,c.agent_id,c.credit_amount amount,ABS(c.credit_amount) gross_amount,MAX(ABS(c.credit_amount-c.approved_amount),ABS(c.credit_amount-a.approved_amount)) direct_amount FROM credits_adjustments c LEFT JOIN approvals a ON c.approval_id=a.approval_id WHERE c.credit_status='Posted' AND c.approval_status='Approved' AND (ABS(c.credit_amount-c.approved_amount)>0.01 OR ABS(c.credit_amount-a.approved_amount)>0.01)) q;


-- ===== Source file: 05_reason_and_documentation_tests.sql =====

-- SQLite-compatible audit queries. Each statement returns a standardized record-level population.
-- T21-T23 remain Python-primary normalized behavioral indicators.

SELECT 'T09' AS test_id, record_id AS record_id, COALESCE(account_id,'') AS account_id, COALESCE(customer_id,'') AS customer_id, COALESCE(agent_id,'') AS agent_id, CAST(amount AS REAL) AS transaction_amount, CAST(gross_amount AS REAL) AS gross_flagged_amount, CAST(direct_amount AS REAL) AS direct_measurable_amount FROM (SELECT c.credit_id record_id,c.account_id,c.customer_id,c.agent_id,c.credit_amount amount,CASE WHEN c.credit_status='Posted' THEN ABS(c.credit_amount) ELSE 0 END gross_amount,0 direct_amount FROM credits_adjustments c LEFT JOIN reason_codes r ON c.reason_code=r.reason_code WHERE r.reason_code IS NULL OR CAST(COALESCE(r.active_flag,0) AS INTEGER)<>1) q;

SELECT 'T10' AS test_id, record_id AS record_id, COALESCE(account_id,'') AS account_id, COALESCE(customer_id,'') AS customer_id, COALESCE(agent_id,'') AS agent_id, CAST(amount AS REAL) AS transaction_amount, CAST(gross_amount AS REAL) AS gross_flagged_amount, CAST(direct_amount AS REAL) AS direct_measurable_amount FROM (SELECT c.credit_id record_id,c.account_id,c.customer_id,c.agent_id,c.credit_amount amount,ABS(c.credit_amount) gross_amount,0 direct_amount FROM credits_adjustments c JOIN reason_codes r ON c.reason_code=r.reason_code WHERE c.credit_status='Posted' AND c.credit_type<>r.credit_type) q;

SELECT 'T11' AS test_id, record_id AS record_id, COALESCE(account_id,'') AS account_id, COALESCE(customer_id,'') AS customer_id, COALESCE(agent_id,'') AS agent_id, CAST(amount AS REAL) AS transaction_amount, CAST(gross_amount AS REAL) AS gross_flagged_amount, CAST(direct_amount AS REAL) AS direct_measurable_amount FROM (SELECT c.credit_id record_id,c.account_id,c.customer_id,c.agent_id,c.credit_amount amount,ABS(c.credit_amount) gross_amount,0 direct_amount FROM credits_adjustments c LEFT JOIN cases_disputes ca ON c.case_id=ca.case_id WHERE c.credit_status='Posted' AND COALESCE(c.interaction_id,'')<>'' AND (COALESCE(c.case_id,'')='' OR ca.case_id IS NULL)) q;

SELECT 'T12' AS test_id, record_id AS record_id, COALESCE(account_id,'') AS account_id, COALESCE(customer_id,'') AS customer_id, COALESCE(agent_id,'') AS agent_id, CAST(amount AS REAL) AS transaction_amount, CAST(gross_amount AS REAL) AS gross_flagged_amount, CAST(direct_amount AS REAL) AS direct_measurable_amount FROM (SELECT c.credit_id record_id,c.account_id,c.customer_id,c.agent_id,c.credit_amount amount,ABS(c.credit_amount) gross_amount,0 direct_amount FROM credits_adjustments c LEFT JOIN interactions i ON c.interaction_id=i.interaction_id WHERE c.credit_status='Posted' AND COALESCE(c.case_id,'')<>'' AND (COALESCE(c.interaction_id,'')='' OR i.interaction_id IS NULL)) q;

SELECT 'T13' AS test_id, record_id AS record_id, COALESCE(account_id,'') AS account_id, COALESCE(customer_id,'') AS customer_id, COALESCE(agent_id,'') AS agent_id, CAST(amount AS REAL) AS transaction_amount, CAST(gross_amount AS REAL) AS gross_flagged_amount, CAST(direct_amount AS REAL) AS direct_measurable_amount FROM (SELECT c.credit_id record_id,c.account_id,c.customer_id,c.agent_id,c.credit_amount amount,ABS(c.credit_amount) gross_amount,0 direct_amount FROM credits_adjustments c JOIN cases_disputes ca ON c.case_id=ca.case_id JOIN interactions i ON c.interaction_id=i.interaction_id WHERE c.credit_status='Posted' AND (CAST(c.documentation_complete_flag AS INTEGER)<>1 OR CAST(ca.supporting_documentation_flag AS INTEGER)<>1)) q;

SELECT 'T14' AS test_id, record_id AS record_id, COALESCE(account_id,'') AS account_id, COALESCE(customer_id,'') AS customer_id, COALESCE(agent_id,'') AS agent_id, CAST(amount AS REAL) AS transaction_amount, CAST(gross_amount AS REAL) AS gross_flagged_amount, CAST(direct_amount AS REAL) AS direct_measurable_amount FROM (SELECT c.credit_id record_id,c.account_id,c.customer_id,c.agent_id,c.credit_amount amount,ABS(c.credit_amount) gross_amount,0 direct_amount FROM credits_adjustments c JOIN interactions i ON c.interaction_id=i.interaction_id WHERE c.credit_status='Posted' AND CAST(c.customer_notified_flag AS INTEGER)<>1) q;

SELECT 'T15' AS test_id, record_id AS record_id, COALESCE(account_id,'') AS account_id, COALESCE(customer_id,'') AS customer_id, COALESCE(agent_id,'') AS agent_id, CAST(amount AS REAL) AS transaction_amount, CAST(gross_amount AS REAL) AS gross_flagged_amount, CAST(direct_amount AS REAL) AS direct_measurable_amount FROM (SELECT c.credit_id record_id,c.account_id,c.customer_id,c.agent_id,c.credit_amount amount,ABS(c.credit_amount) gross_amount,0 direct_amount FROM credits_adjustments c JOIN interactions i ON c.interaction_id=i.interaction_id WHERE c.credit_status='Posted' AND CAST(i.authentication_completed_flag AS INTEGER)<>1) q;


-- ===== Source file: 06_employee_access_and_sod_tests.sql =====

-- SQLite-compatible audit queries. Each statement returns a standardized record-level population.
-- T21-T23 remain Python-primary normalized behavioral indicators.

SELECT 'T16' AS test_id, record_id AS record_id, COALESCE(account_id,'') AS account_id, COALESCE(customer_id,'') AS customer_id, COALESCE(agent_id,'') AS agent_id, CAST(amount AS REAL) AS transaction_amount, CAST(gross_amount AS REAL) AS gross_flagged_amount, CAST(direct_amount AS REAL) AS direct_measurable_amount FROM (SELECT credit_id record_id,account_id,customer_id,agent_id,credit_amount amount,ABS(credit_amount) gross_amount,0 direct_amount FROM credits_adjustments WHERE credit_status='Posted' AND CAST(manual_override_flag AS INTEGER)=1 AND approval_status<>'Approved') q;

SELECT 'T17' AS test_id, record_id AS record_id, COALESCE(account_id,'') AS account_id, COALESCE(customer_id,'') AS customer_id, COALESCE(agent_id,'') AS agent_id, CAST(amount AS REAL) AS transaction_amount, CAST(gross_amount AS REAL) AS gross_flagged_amount, CAST(direct_amount AS REAL) AS direct_measurable_amount FROM (SELECT credit_id record_id,account_id,customer_id,agent_id,credit_amount amount,ABS(credit_amount) gross_amount,0 direct_amount FROM credits_adjustments WHERE credit_status='Posted' AND CAST(after_hours_flag AS INTEGER)=1 AND (approval_status<>'Approved' OR CAST(documentation_complete_flag AS INTEGER)<>1)) q;

SELECT 'T18' AS test_id, record_id AS record_id, COALESCE(account_id,'') AS account_id, COALESCE(customer_id,'') AS customer_id, COALESCE(agent_id,'') AS agent_id, CAST(amount AS REAL) AS transaction_amount, CAST(gross_amount AS REAL) AS gross_flagged_amount, CAST(direct_amount AS REAL) AS direct_measurable_amount FROM (SELECT c.credit_id record_id,c.account_id,c.customer_id,c.agent_id,c.credit_amount amount,CASE WHEN c.credit_status='Posted' THEN ABS(c.credit_amount) ELSE 0 END gross_amount,0 direct_amount FROM credits_adjustments c LEFT JOIN agents a ON c.agent_id=a.agent_id WHERE COALESCE(a.employment_status,'')<>'Active') q;

SELECT 'T19' AS test_id, record_id AS record_id, COALESCE(account_id,'') AS account_id, COALESCE(customer_id,'') AS customer_id, COALESCE(agent_id,'') AS agent_id, CAST(amount AS REAL) AS transaction_amount, CAST(gross_amount AS REAL) AS gross_flagged_amount, CAST(direct_amount AS REAL) AS direct_measurable_amount FROM (SELECT c.credit_id record_id,c.account_id,c.customer_id,c.agent_id,c.credit_amount amount,CASE WHEN c.credit_status='Posted' THEN ABS(c.credit_amount) ELSE 0 END gross_amount,0 direct_amount FROM credits_adjustments c LEFT JOIN approvals a ON c.approval_id=a.approval_id WHERE c.agent_id=c.supervisor_id OR c.agent_id=a.supervisor_id) q;

SELECT 'T20' AS test_id, record_id AS record_id, COALESCE(account_id,'') AS account_id, COALESCE(customer_id,'') AS customer_id, COALESCE(agent_id,'') AS agent_id, CAST(amount AS REAL) AS transaction_amount, CAST(gross_amount AS REAL) AS gross_flagged_amount, CAST(direct_amount AS REAL) AS direct_measurable_amount FROM (SELECT c.credit_id record_id,c.account_id,c.customer_id,c.agent_id,c.credit_amount amount,CASE WHEN c.credit_status='Posted' THEN ABS(c.credit_amount) ELSE 0 END gross_amount,0 direct_amount FROM credits_adjustments c JOIN accounts ac ON c.account_id=ac.account_id WHERE c.customer_id<>ac.customer_id) q;


-- ===== Source file: 10_dispute_closure_tests.sql =====

-- SQLite-compatible audit queries. Each statement returns a standardized record-level population.
-- T21-T23 remain Python-primary normalized behavioral indicators.

SELECT 'T33' AS test_id, record_id AS record_id, COALESCE(account_id,'') AS account_id, COALESCE(customer_id,'') AS customer_id, COALESCE(agent_id,'') AS agent_id, CAST(amount AS REAL) AS transaction_amount, CAST(gross_amount AS REAL) AS gross_flagged_amount, CAST(direct_amount AS REAL) AS direct_measurable_amount FROM (SELECT case_id record_id,account_id,customer_id,assigned_agent_id agent_id,COALESCE(disputed_amount,0) amount,ABS(COALESCE(disputed_amount,0)) gross_amount,0 direct_amount FROM cases_disputes WHERE case_status='Closed' AND (COALESCE(resolution_code,'')='' OR COALESCE(resolution_summary,'')='')) q;
