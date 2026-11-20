"""Score reviewer predictions against Billy's manually reviewed reference labels.

Usage:
    python ai_review/evaluate.py baseline     # scores results/baseline_predictions.csv
    python ai_review/evaluate.py claude       # scores results/claude_predictions.csv
    python ai_review/evaluate.py both         # both, plus a side-by-side table

Writes results/<name>_eval.md and results/<name>_errors.csv (every disagreement, for failure analysis).
"""
import csv
import sys
from collections import Counter

from openpyxl import load_workbook

from common import DATA, RESULTS, ROOT, review_flags

REFERENCE = ROOT / "reference_labels.xlsx"  # Billy's own labels, all 150 calls
KEY = DATA / "planted_problems_key.csv"  # used only for planted-problem types

SHEET_MAP = {
    "q1_answer": "Q1 Promise", "q1_amount": "Q1 Amount", "q2_answer": "Q2 Complaint",
    "q2_customer_asked_for_credit": "Q2 Customer asked for credit", "q3_answer": "Q3 Notes",
    "q3_field_at_issue": "Q3 Field at issue", "q3_coaching": "Q3 Coaching", "q4_answer": "Q4 Resolved",
}
CHECKS = [
    ("Q1 promise", "q1_answer"), ("Q1 amount", "q1_amount"), ("Q2 complaint", "q2_answer"),
    ("Q2 asked for credit", "q2_customer_asked_for_credit"), ("Q3 notes", "q3_answer"),
    ("Q3 field at issue", "q3_field_at_issue"), ("Q3 coaching", "q3_coaching"), ("Q4 resolved", "q4_answer"),
    ("Needs human review", "needs_human_review"),
]


def load_reference():
    ws = load_workbook(REFERENCE, read_only=True, data_only=True)["Labels"]
    rows = list(ws.iter_rows(values_only=True))
    hdr = rows[0]
    ref = {}
    for r in rows[1:]:
        d = dict(zip(hdr, r))
        p = {k: ("" if d[v] is None else d[v]) for k, v in SHEET_MAP.items()}
        notes = str(d.get("Notes") or "")
        p["q1_confidence"] = notes.split("Q1 confidence: ")[-1].strip() if "Q1 confidence: " in notes else "High"
        p["needs_human_review"], _ = review_flags(p)
        ref[d["Call ID"]] = p
    return ref


def same(field, a, b):
    if field == "q1_amount":
        if a in ("", None) and b in ("", None):
            return True
        try:
            return abs(float(a) - float(b)) < 0.01
        except (TypeError, ValueError):
            return False
    return str(a).strip() == str(b).strip()


def evaluate(name):
    path = RESULTS / f"{name}_predictions.csv"
    if not path.exists():
        sys.exit(f"{path.name} not found. Run the {name} reviewer first.")
    pred = {r["call_id"]: r for r in csv.DictReader(open(path, newline=""))}
    ref = load_reference()
    key = {r["call_id"]: r for r in csv.DictReader(open(KEY, newline=""))}
    ids = [c for c in ref if c in pred]

    acc, errors = {}, []
    for label, f in CHECKS:
        ok = 0
        for c in ids:
            if same(f, pred[c].get(f, ""), ref[c][f]):
                ok += 1
            else:
                errors.append({"call_id": c, "check": label, "reference": ref[c][f], "predicted": pred[c].get(f, ""),
                               "planted_problem": key[c]["planted_problem"], "scenario": key[c]["scenario"]})
        acc[label] = (ok, len(ids))

    # Problem detection: any Q3 answer other than Match counts as "flagged".
    tp = sum(1 for c in ids if ref[c]["q3_answer"] != "Match" and pred[c]["q3_answer"] != "Match")
    fp = sum(1 for c in ids if ref[c]["q3_answer"] == "Match" and pred[c]["q3_answer"] != "Match")
    fn = sum(1 for c in ids if ref[c]["q3_answer"] != "Match" and pred[c]["q3_answer"] == "Match")
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    by_type = Counter(key[c]["planted_problem"] for c in ids if key[c]["planted_problem"])
    caught = Counter(key[c]["planted_problem"] for c in ids if key[c]["planted_problem"] and pred[c]["q3_answer"] != "Match")
    routed = sum(1 for c in ids if pred[c]["needs_human_review"] == "Yes")

    lines = [f"# Evaluation: {name}", "", f"Calls scored: {len(ids)} of {len(ref)}", "",
             "## Agreement with the reference labels (labeled by Billy)", "",
             "| Check | Agreement |", "|---|---|"]
    lines += [f"| {k} | {ok}/{n} ({ok / n:.0%}) |" for k, (ok, n) in acc.items()]
    lines += ["", "## Problem detection (Q3 not Match)", "",
              f"- Precision: {precision:.0%} (of calls flagged, share that really had a problem)",
              f"- Recall: {recall:.0%} (of real problems, share that were flagged)",
              f"- False alarms on clean calls: {fp}", "",
              "| Planted problem | Caught |", "|---|---|"]
    lines += [f"| {t} | {caught[t]}/{n} |" for t, n in sorted(by_type.items())]
    lines += ["", f"Calls sent to human review: {routed}/{len(ids)} ({routed / len(ids):.0%})"]
    (RESULTS / f"{name}_eval.md").write_text("\n".join(lines) + "\n")
    with open(RESULTS / f"{name}_errors.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["call_id", "check", "reference", "predicted", "planted_problem", "scenario"])
        w.writeheader()
        w.writerows(errors)
    print("\n".join(lines))
    return acc, precision, recall, routed, len(ids)


def main():
    which = sys.argv[1] if len(sys.argv) > 1 else "baseline"
    other = sys.argv[2] if len(sys.argv) > 2 else "claude"  # e.g. "claude_helpers"
    names = ["baseline", other] if which == "both" else [which]
    out = {n: evaluate(n) for n in names}
    if len(out) == 2:
        b, c = out["baseline"], out[other]
        lines = [f"# Baseline vs {other}", "", f"| Check | Baseline | {other} |", "|---|---|---|"]
        for k in b[0]:
            lines.append(f"| {k} | {b[0][k][0] / b[0][k][1]:.0%} | {c[0][k][0] / c[0][k][1]:.0%} |")
        lines += [f"| Problem precision | {b[1]:.0%} | {c[1]:.0%} |", f"| Problem recall | {b[2]:.0%} | {c[2]:.0%} |",
                  f"| Sent to human review | {b[3] / b[4]:.0%} | {c[3] / c[4]:.0%} |"]
        (RESULTS / f"comparison_baseline_vs_{other}.md").write_text("\n".join(lines) + "\n")
        print("\n" + "\n".join(lines))


if __name__ == "__main__":
    main()
