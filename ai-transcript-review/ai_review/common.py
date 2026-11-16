"""Shared helpers: load calls, the prediction format, and the human-review rules."""
import csv
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
RESULTS = ROOT / "results"

PRED_COLUMNS = [
    "call_id",
    "q1_answer", "q1_amount", "q1_type", "q1_turn", "q1_confidence",
    "q2_answer", "q2_disputed_item", "q2_customer_asked_for_credit", "q2_turn", "q2_confidence",
    "q3_answer", "q3_field_at_issue", "q3_coaching", "q3_confidence", "q3_explanation",
    "q4_answer", "q4_turn", "q4_confidence",
    "needs_human_review", "review_reasons", "one_line_summary",
]


def load_calls():
    """Return a list of calls: record fields plus ordered transcript turns."""
    turns = defaultdict(list)
    with open(DATA / "matched_transcripts.csv", newline="") as f:
        for r in csv.DictReader(f):
            turns[r["call_id"]].append((int(r["turn_number"]), r["speaker"], r["utterance"]))
    calls = []
    with open(DATA / "matched_interactions.csv", newline="") as f:
        for r in csv.DictReader(f):
            r["turns"] = sorted(turns[r["call_id"]])
            calls.append(r)
    return calls


def transcript_text(call):
    return "\n".join(f"[{n}] {who}: {text}" for n, who, text in call["turns"])


def review_flags(p):
    """Apply Billy's human-review rules to one prediction dict. Returns (Yes/No, reasons)."""
    reasons = []
    for q in ("q1", "q2", "q3", "q4"):
        if p.get(f"{q}_confidence") == "Low":
            reasons.append(f"{q.upper()} low confidence")
    if p.get("q3_answer") == "Contradicts":
        reasons.append("Q3 contradicts")
    amt = p.get("q1_amount")
    amt = float(amt) if amt not in (None, "") else None
    if p.get("q1_answer") == "Yes (firm)" and amt is not None and amt > 50:
        reasons.append("Q1 firm promise over $50")
    if str(p.get("q1_answer", "")).startswith("Yes") and amt is None:
        reasons.append("Q1 promise with no amount")
    if p.get("q4_answer") in ("Not resolved", "Unclear"):
        reasons.append("Q4 not resolved or unclear")
    return ("Yes" if reasons else "No"), "; ".join(reasons)


def write_predictions(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=PRED_COLUMNS)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in PRED_COLUMNS})
