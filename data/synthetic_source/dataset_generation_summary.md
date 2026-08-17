# Dataset Generation Summary

- Fictional company: **Orivanta Home Services**
- Random seed: **20260712**
- Seeded exceptions/data-quality findings: **481**
- Transcript interactions: **650**
- Transcript turn rows: **6051**
- Distinct transcript pattern combinations: **54**

## Row counts

- `account_reconciliations`: 3,500
- `accounts`: 3,500
- `agents`: 60
- `approvals`: 820
- `audit_control_matrix`: 20
- `audit_exceptions_answer_key`: 481
- `cases_disputes`: 1,250
- `charges`: 8,515
- `control_rules`: 20
- `credits_adjustments`: 2,040
- `customers`: 3,000
- `data_dictionary`: 263
- `interactions`: 1,300
- `locations`: 8
- `payments`: 4,200
- `products_services`: 20
- `reason_codes`: 24
- `supervisors`: 8
- `transcripts`: 6,051

## Exception category counts

- `ACCOUNT_RECONCILIATION_DIFFERENCE`: 20
- `AFTER_HOURS_NO_REVIEW`: 15
- `APPROVAL_AFTER_POSTING`: 15
- `APPROVED_POSTED_AMOUNT_MISMATCH`: 15
- `CHARGE_REVERSAL_INVALID_ORIGINAL`: 10
- `CLOSED_CASE_NO_RESOLUTION`: 15
- `COMPLAINT_CONTRADICTS_AGENT_NOTES`: 15
- `COPIED_NOTES_ACROSS_CASES`: 10
- `CREDIT_ABOVE_AUTHORITY_NO_APPROVAL`: 25
- `CREDIT_EXCEEDS_ORIGINAL_CHARGE`: 20
- `CREDIT_WRONG_CUSTOMER`: 12
- `DATA_QUALITY_INCONSISTENT_CAPITALIZATION`: 6
- `DATA_QUALITY_MISSING_AGENT_NOTES`: 6
- `DATA_QUALITY_MISSING_END_TIME`: 8
- `DUPLICATE_CHARGE`: 15
- `DUPLICATE_CREDIT`: 20
- `EXCESSIVE_AGENT_CREDIT_CONCENTRATION`: 20
- `INACTIVE_AGENT_POSTING`: 10
- `INVALID_REASON_CODE`: 15
- `MANUAL_OVERRIDE_NO_APPROVAL`: 15
- `MONTH_END_CREDIT_CONCENTRATION`: 15
- `NO_SUPPORTING_CASE`: 18
- `NO_SUPPORTING_INTERACTION`: 18
- `POSTED_CREDIT_NOT_COMMUNICATED`: 15
- `PROMISED_CREDIT_NOT_POSTED`: 20
- `PROMOTION_OUTSIDE_EFFECTIVE_PERIOD`: 12
- `REPEATED_CUSTOMER_CREDITS`: 15
- `REVERSAL_WITHOUT_VALID_ORIGINAL`: 12
- `SELF_APPROVAL`: 10
- `SERVICE_CREDIT_NO_OUTAGE_EVIDENCE`: 12
- `SPLIT_CREDIT_THRESHOLD_AVOIDANCE`: 20
- `SUMMARY_INCONSISTENT_WITH_CASE`: 15
- `SUSPICIOUS_AGENT_CUSTOMER_PAIRING`: 12

## Recommended starting point

Begin with credits, agents, approvals, reason codes, and charges. Do not inspect the answer key until your independent testing is complete.