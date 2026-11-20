# SQL files

SQLite versions of the audit tests. Each test is one query that returns the records it flags, in a standard set of columns. Each query starts with a comment giving the test ID, its name and the rule it applies.

| File | Tests |
|---|---|
| `core_audit_tests.sql` | Authorization and approval, credit accuracy, reason codes, documentation, access and override tests |
| `documentation_and_approval_tests.sql` | Documentation, promised adjustments and transcript tests (T09–T15 also appear in the core file) |
| `duplicate_and_split_credit_tests.sql` | Exact duplicates, near-duplicates, split credits and duplicate charges |
| `reconciliation_tests.sql` | Account reconciliation tests |
| `final_exception_output.sql` | All 37 SQL-supported tests combined into one exception list |

Run them against `data/synthetic_source/orivanta_audit_analytics.sqlite` in any SQLite client.

The SQL results are reconciled to the Python results at the record-ID level: all 37 SQL-supported tests match. Three behavioral tests (T21–T23) are Python-only because they rely on percentile-style logic that is easier to maintain in Python.
