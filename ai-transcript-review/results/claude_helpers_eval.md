> **Historical snapshot (Nov 11, 2026):** scored against my labels before 14 Q3 labels were changed on Nov 16. Rerunning `evaluate.py` will overwrite it with scores against the current labels.

# Evaluation: claude_helpers

Calls scored: 150 of 150

## Agreement with the reference labels (manually reviewed by Billy)

| Check | Agreement |
|---|---|
| Q1 promise | 141/150 (94%) |
| Q1 amount | 150/150 (100%) |
| Q2 complaint | 150/150 (100%) |
| Q2 asked for credit | 150/150 (100%) |
| Q3 notes | 146/150 (97%) |
| Q3 field at issue | 146/150 (97%) |
| Q3 coaching | 146/150 (97%) |
| Q4 resolved | 132/150 (88%) |
| Needs human review | 144/150 (96%) |

## Problem detection (Q3 not Match)

- Precision: 96% (of calls flagged, share that really had a problem)
- Recall: 96% (of real problems, share that were flagged)
- False alarms on clean calls: 2

| Planted problem | Caught |
|---|---|
| NOTES_CONTRADICT_CALL | 8/8 |
| NOTES_MISSING | 8/8 |
| PROMISE_OMITTED_FROM_NOTES | 8/8 |
| RECORD_AMOUNT_MISMATCH | 8/8 |
| RECORD_OVERSTATES_PROMISE | 4/6 |
| RECORD_SAYS_NO_PROMISE | 7/7 |
| SUMMARY_SAYS_RESOLVED | 5/5 |

Calls sent to human review: 103/150 (69%)
