# Evaluation: claude

Calls scored: 150 of 150

## Agreement with the reference labels (labeled by Billy)

| Check | Agreement |
|---|---|
| Q1 promise | 150/150 (100%) |
| Q1 amount | 150/150 (100%) |
| Q2 complaint | 150/150 (100%) |
| Q2 asked for credit | 150/150 (100%) |
| Q3 notes | 150/150 (100%) |
| Q3 field at issue | 149/150 (99%) |
| Q3 coaching | 150/150 (100%) |
| Q4 resolved | 150/150 (100%) |
| Needs human review | 150/150 (100%) |

## Problem detection (Q3 not Match)

- Precision: 100% (of calls flagged, share that really had a problem)
- Recall: 100% (of real problems, share that were flagged)
- False alarms on clean calls: 0

| Planted problem | Caught |
|---|---|
| NOTES_CONTRADICT_CALL | 8/8 |
| NOTES_MISSING | 8/8 |
| PROMISE_OMITTED_FROM_NOTES | 8/8 |
| RECORD_AMOUNT_MISMATCH | 8/8 |
| RECORD_OVERSTATES_PROMISE | 6/6 |
| RECORD_SAYS_NO_PROMISE | 7/7 |
| SUMMARY_SAYS_RESOLVED | 5/5 |

Calls sent to human review: 99/150 (66%)
