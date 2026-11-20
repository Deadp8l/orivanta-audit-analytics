# Evaluation: baseline

Calls scored: 150 of 150

## Agreement with the reference labels (labeled by Billy)

| Check | Agreement |
|---|---|
| Q1 promise | 150/150 (100%) |
| Q1 amount | 150/150 (100%) |
| Q2 complaint | 150/150 (100%) |
| Q2 asked for credit | 150/150 (100%) |
| Q3 notes | 97/150 (65%) |
| Q3 field at issue | 97/150 (65%) |
| Q3 coaching | 97/150 (65%) |
| Q4 resolved | 124/150 (83%) |
| Needs human review | 125/150 (83%) |

## Problem detection (Q3 not Match)

- Precision: 100% (of calls flagged, share that really had a problem)
- Recall: 23% (of real problems, share that were flagged)
- False alarms on clean calls: 0

| Planted problem | Caught |
|---|---|
| NOTES_CONTRADICT_CALL | 0/8 |
| NOTES_MISSING | 8/8 |
| PROMISE_OMITTED_FROM_NOTES | 0/8 |
| RECORD_AMOUNT_MISMATCH | 8/8 |
| RECORD_OVERSTATES_PROMISE | 0/6 |
| RECORD_SAYS_NO_PROMISE | 0/7 |
| SUMMARY_SAYS_RESOLVED | 0/5 |

Calls sent to human review: 104/150 (69%)
