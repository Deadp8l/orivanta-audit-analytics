> **Historical snapshot (Nov 11, 2026):** scored against Billy's labels before 14 Q3 labels were changed on Nov 16. Rerunning `evaluate.py` will overwrite it with scores against the current labels.

# Baseline vs claude_helpers

| Check | Baseline | claude_helpers |
|---|---|---|
| Q1 promise | 100% | 94% |
| Q1 amount | 100% | 100% |
| Q2 complaint | 100% | 100% |
| Q2 asked for credit | 100% | 100% |
| Q3 notes | 74% | 97% |
| Q3 field at issue | 74% | 97% |
| Q3 coaching | 74% | 97% |
| Q4 resolved | 83% | 88% |
| Needs human review | 83% | 96% |
| Problem precision | 100% | 96% |
| Problem recall | 29% | 96% |
| Sent to human review | 69% | 69% |
