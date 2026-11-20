# Raw outputs: rubric v1.2 (Nov 11, 2026)

Historical. These 10 files are the raw answers from the rubric v1.2 run, kept so the v1.2 scores in [`../RESULTS_SUMMARY.md`](../RESULTS_SUMMARY.md) can be checked.

- Each file (`out_01.json` to `out_10.json`) holds 15 calls, reviewed by a separate Claude session that got only rubric v1.2, the output schema and those 15 calls.
- `ai_review/collect_helper_reviews.py results/helper_raw` validates them against the schema, applies the human-review rules in code and writes `results/claude_helpers_predictions.csv`.
- The current results (rubric v1.3) come from `ai_review/run_claude_review.py`, one request per call, not from these files.
