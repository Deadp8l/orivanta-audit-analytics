"""Keyword baseline: the simple rules a team might write before trying AI.

It looks for fixed phrases in the transcript and compares the recorded amount with
amounts said on the call. No AI is used. It sets the bar the Claude reviewer must beat.

Usage: python ai_review/run_baseline.py
"""
import re

from common import RESULTS, load_calls, review_flags, write_predictions

MONEY = re.compile(r"\$(\d[\d,]*\.\d\d)")
FIRM = re.compile(r"\b(I've applied|I've processed|I've reapplied|I am correcting|I'm correcting)\b", re.I)
COND = re.compile(r"\b(request|submit|submitting|review|escalat|see what I can do|ticket)\w*", re.I)
CREDIT_ASK = re.compile(r"credit|refund|take that off", re.I)
DONE_NOW = re.compile(r"(shows on your account now|on the account now)", re.I)
LATER = re.compile(r"(business days|call you back|within|will contact|email)", re.I)


def amounts(text):
    return [float(m.replace(",", "")) for m in MONEY.findall(text)]


def predict(call):
    agent = [(n, t) for n, who, t in call["turns"] if who == "Agent"]
    cust = [(n, t) for n, who, t in call["turns"] if who == "Customer"]
    p = {"call_id": call["call_id"]}

    # Q1: first agent line with a firm phrase, else a conditional phrase.
    firm = [(n, t) for n, t in agent if FIRM.search(t)]
    cond = [(n, t) for n, t in agent if COND.search(t) and "credit" in t.lower() or re.search(r"adjustment request|billing review", t, re.I)]
    hit = firm[0] if firm else (cond[0] if cond else None)
    if hit:
        p["q1_answer"] = "Yes (firm)" if firm else "Yes (conditional)"
        a = amounts(hit[1])
        p["q1_amount"] = a[0] if a else ""
        p["q1_type"] = "Refund" if "refund" in hit[1].lower() else "Promotion" if "discount" in hit[1].lower() else "Credit"
        p["q1_turn"] = hit[0]
    else:
        p.update(q1_answer="No", q1_amount="", q1_type="None", q1_turn="")
    p["q1_confidence"] = "High"

    # Q2: the customer's first line is treated as the complaint.
    p["q2_answer"] = "Yes" if cust else "Unclear"
    p["q2_turn"] = cust[0][0] if cust else ""
    p["q2_disputed_item"] = call["contact_reason"]
    p["q2_customer_asked_for_credit"] = "Yes" if any(CREDIT_ASK.search(t) for _, t in cust) else "No"
    p["q2_confidence"] = "High"

    # Q3: blank notes -> Missing; recorded amount not said on the call -> Contradicts.
    said = amounts(" ".join(t for _, _, t in call["turns"]))
    rec = float(call["promised_amount"])
    if not call["agent_notes"].strip():
        p.update(q3_answer="Missing", q3_field_at_issue="Notes", q3_coaching="Yes")
    elif rec > 0 and all(abs(rec - s) > 0.009 for s in said):
        p.update(q3_answer="Contradicts", q3_field_at_issue="Amount", q3_coaching="Yes")  # rubric v1.2
    else:
        p.update(q3_answer="Match", q3_field_at_issue="None", q3_coaching="No")
    p["q3_confidence"] = "High"

    # Q4: done-now phrase -> Resolved; later phrase -> follow-up pending; else Not resolved.
    text = " ".join(t for _, t in agent)
    p["q4_answer"] = "Resolved" if DONE_NOW.search(text) else "Resolved - follow-up pending" if LATER.search(text) else "Not resolved"
    p["q4_turn"] = ""
    p["q4_confidence"] = "High"

    p["needs_human_review"], p["review_reasons"] = review_flags(p)
    return p


if __name__ == "__main__":
    rows = [predict(c) for c in load_calls()]
    write_predictions(RESULTS / "baseline_predictions.csv", rows)
    print(f"Saved {len(rows)} baseline predictions to results/baseline_predictions.csv")
