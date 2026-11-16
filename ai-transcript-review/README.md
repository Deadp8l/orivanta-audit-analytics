# Orivanta AI Transcript Review

An AI reviewer that reads synthetic customer-care calls, checks them against a written rubric, and routes risky calls to a person. It is scored against my own labels for all 150 calls.

> **Synthetic data only.** Orivanta Home Services is fictional. No employer, client or proprietary data, criteria or templates are used.

**Start with the [case study](CASE_STUDY.md).** Full results are in [`results/RESULTS_SUMMARY.md`](results/RESULTS_SUMMARY.md).

## Headline (rubric v1.3, 150 calls)

| Check | Keyword rules | Claude |
|---|---|---|
| Planted problems caught | 23% | 100% (50 of 50) |
| False alarms on clean calls | 0 | 0 |
| Human-review decision agrees with my labels | 83% | 100% |

The rubric was refined on these same 150 calls, so these numbers show agreement on the tuning set, not accuracy on new calls. See the case study's limits section.

## What's here
- `CASE_STUDY.md`: the problem, rubric, evaluation, what the disagreements taught me, and limits
- `ai_review/rubric.md`: my review rubric (v1.3), with its change log
- `ai_review/run_baseline.py`: keyword-rules reviewer (no AI)
- `ai_review/run_claude_review.py`: Claude reviewer (`claude-opus-5-5`, structured JSON output, one request per call)
- `ai_review/evaluate.py`: scores either reviewer against the reference labels
- `ai_review/collect_helper_reviews.py`: collects the v1.2 helper-session outputs in `results/helper_raw/`
- `Orivanta_Matched_Labeling_Sheet_BILLY.xlsx`: reference labels for all 150 calls, manually reviewed by Billy
- `data/`: 150 matched synthetic calls (records and transcripts) and the answer key of planted problems. The key was kept closed while labeling and is used only to report which planted problems were caught.
- `generate_matched_calls.py`: the script that generated the calls. Labeling later found 5 calls where it wrote the wrong "customer asked for a credit" value; the key in `data/` has those corrections.
- `results/`: predictions, scores and every disagreement

## Run it (from this folder)
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python ai_review/run_baseline.py
```

**Option A: Claude Code login (default, no API key).**
```bash
claude auth login
python ai_review/run_claude_review.py --limit 3   # try 3 calls first
python ai_review/run_claude_review.py             # all 150, about 35 minutes
```

**Option B: Anthropic API key.**
```bash
export ANTHROPIC_API_KEY="your-key"   # stays on your machine; never commit it
python ai_review/run_claude_review.py --backend api
```

Then score both:
```bash
python ai_review/evaluate.py both
```
