"""Generate a matched synthetic call set for the Orivanta AI transcript review module.

Every call's transcript, record fields (promised action, amount, disposition),
summary and agent notes agree by default. About one third of calls then get one
planted problem, and a few get a deliberate rubric edge case. The expected label
for each rubric question is written to a separate answer key.

All data is fictional (Orivanta Home Services). Seed is fixed for reproducibility.
"""
import csv
import random

SEED = 20261111
N_CALLS = 150
rng = random.Random(SEED)


def money(x):
    return f"${x:,.2f}"


GREETINGS = [
    "Thank you for calling Orivanta Home Services. How can I help today?",
    "Orivanta Home Services billing, this is {agent}. What can I look at for you?",
    "Thanks for contacting Orivanta. I can help with account and billing questions.",
    "You've reached Orivanta customer care. What's going on with your account?",
]
AGENT_NAMES = ["Maya", "Elias", "Jordan", "Priya", "Victor", "Lena", "Omar", "Tess"]
ACKS = [
    "I'm sorry about that. Let me pull up the account.",
    "I understand. Give me a moment to open the billing history.",
    "Thanks for explaining. I'll take a look at the charges now.",
    "Let me check that for you. One moment while I review the bill.",
]
VERIFY = [
    ("Before I go into the details, can you confirm the last four digits on the account?",
     "Sure, it ends in {last4}."),
    ("For security, can you confirm the service address city?", "Yes, it's {city}."),
]
CITIES = ["Maple Junction", "Riverglass", "Lake Briar", "Stonefield", "North Ember", "Oak Meridian"]
INVESTIGATE = [
    "I can see the charge on the {month} statement. Let me compare it with your payment history.",
    "I'm looking at the entries now and checking where that amount came from.",
    "I have the invoice open and I'm reviewing the line items.",
]
MONTHS = ["March", "April", "May", "June", "July", "August"]
CLOSE_THANKS = [
    "Is there anything else I can help with today?",
    "Thanks for your patience. Anything else on the account?",
]
CUST_BYE = ["No, that's all. Thank you.", "That's it, thanks.", "Okay. Thanks for your help."]

# contact reason -> opening line template, short topic for notes
REASONS = {
    "Duplicate charge": ("I was charged {amt} twice on this bill.", "duplicate charge"),
    "Late fee on autopay": ("There's a {amt} late fee, but I'm on autopay.", "late fee"),
    "Service outage": ("My service was out for two days and I'm still billed {amt} for the month.", "service outage"),
    "Equipment return": ("I returned the modem last month, but I'm still being charged {amt} for it.", "equipment fee"),
    "Missing promotion": ("My {amt} monthly discount isn't on this bill.", "missing promotion"),
    "Unrecognized charge": ("There's a {amt} charge on my bill that I don't recognize.", "unrecognized charge"),
    "Installation fee": ("I was charged {amt} for an installation that never happened.", "installation fee"),
}
CREDIT_ASKS = ["Can you credit that back?", "I'd like that refunded.", "Can you take that off the bill?"]

# scenario -> allowed reasons
SCENARIOS = {
    "applied_credit": ["Duplicate charge", "Late fee on autopay", "Installation fee", "Unrecognized charge"],
    "conditional_request": ["Service outage", "Late fee on autopay", "Unrecognized charge", "Duplicate charge"],
    "followup_review": ["Unrecognized charge", "Service outage", "Installation fee"],
    "explained_no_promise": ["Unrecognized charge", "Late fee on autopay"],
    "refund_processed": ["Equipment return", "Duplicate charge"],
    "callback": ["Unrecognized charge", "Installation fee"],
    "promotion_applied": ["Missing promotion"],
    "unresolved": ["Unrecognized charge", "Service outage", "Equipment return"],
}
SCENARIO_WEIGHTS = {
    "applied_credit": 24, "conditional_request": 26, "followup_review": 18, "explained_no_promise": 18,
    "refund_processed": 18, "callback": 15, "promotion_applied": 15, "unresolved": 16,
}
PROMISE_SCENARIOS = {"applied_credit", "conditional_request", "followup_review", "refund_processed", "promotion_applied"}

# planted problem -> scenarios it can apply to
PROBLEMS = {
    "NOTES_CONTRADICT_CALL": None,  # any scenario
    "PROMISE_OMITTED_FROM_NOTES": PROMISE_SCENARIOS,
    "RECORD_AMOUNT_MISMATCH": {"applied_credit", "conditional_request", "refund_processed", "promotion_applied"},
    "RECORD_SAYS_NO_PROMISE": PROMISE_SCENARIOS,
    "RECORD_OVERSTATES_PROMISE": {"conditional_request", "followup_review"},
    "SUMMARY_SAYS_RESOLVED": {"unresolved"},
    "NOTES_MISSING": None,
}
N_PROBLEMS = 50  # about one third
N_EDGE = 8       # vague-promise edge cases; Billy ruled: conditional, Medium confidence


def build_call(n, scenario):
    cid = f"MC{n:04d}"
    reason = rng.choice(SCENARIOS[scenario])
    opening, topic = REASONS[reason]
    amt = round(rng.uniform(6, 160), 2)
    if reason == "Service outage":
        credit = round(amt * rng.choice([0.1, 0.15, 0.2]), 2)
    else:
        credit = amt
    agent = rng.choice(AGENT_NAMES)
    turns = []

    def say(who, text):
        turns.append((who, text))
        return len(turns)

    say("Agent", rng.choice(GREETINGS).format(agent=agent))
    q2_turn = say("Customer", opening.format(amt=money(amt)))
    asked = rng.random() < 0.45 and scenario != "explained_no_promise"
    if asked:
        say("Customer", rng.choice(CREDIT_ASKS))
    say("Agent", rng.choice(ACKS))
    if rng.random() < 0.6:
        q, a = rng.choice(VERIFY)
        say("Agent", q)
        say("Customer", a.format(last4=f"{rng.randint(0, 9999):04d}", city=rng.choice(CITIES)))
    say("Agent", rng.choice(INVESTIGATE).format(month=rng.choice(MONTHS)))

    exp = {"q1": "No", "q1_amount": "", "q1_type": "None", "q1_turn": "", "q1_confidence": "High",
           "q2": "Yes", "q2_asked_credit": "Yes" if asked else "No", "q2_turn": q2_turn,
           "q3": "Match", "q3_field": "None", "q3_coaching": "No", "q4": "", "q4_turn": ""}

    if scenario == "applied_credit":
        t = say("Agent", f"You're right, that was our error. I've applied a {money(credit)} credit, and it shows on your account now.")
        say("Customer", "Great, I can see it. Thank you.")
        exp.update(q1="Yes (firm)", q1_amount=credit, q1_type="Credit", q1_turn=t, q4="Resolved", q4_turn=t)
        rec = ("Issue credit", credit, "Credit issued")
        action = f"applied a {money(credit)} credit"
        notes = f"Confirmed {topic} error; applied {money(credit)} credit. Customer saw it on the account."
    elif scenario == "conditional_request":
        t = say("Agent", f"I can't apply it myself, but I'm submitting a {money(credit)} adjustment request to billing now. You'll get an email once it's reviewed, usually within five business days.")
        say("Customer", "Okay. I'll watch for the email.")
        exp.update(q1="Yes (conditional)", q1_amount=credit, q1_type="Credit", q1_turn=t, q4="Resolved - follow-up pending", q4_turn=t)
        rec = ("Investigate", credit, "Credit requested")
        action = f"submitted a {money(credit)} adjustment request"
        notes = f"Reviewed {topic}; submitted {money(credit)} adjustment request to billing for approval. Customer told to expect an email in 5 business days."
    elif scenario == "followup_review":
        t = say("Agent", "I can't confirm a credit yet, but I've opened a billing review on this charge. The billing team will contact you within three business days.")
        say("Customer", "Fine. Please make sure someone actually calls.")
        exp.update(q1="Yes (conditional)", q1_type="Credit", q1_turn=t, q4="Resolved - follow-up pending", q4_turn=t)
        rec = ("Investigate", 0.0, "Follow-up required")
        action = "opened a billing review"
        notes = f"Could not confirm {topic}; opened billing review for possible credit. Billing to contact customer within 3 business days."
    elif scenario == "explained_no_promise":
        if reason == "Late fee on autopay":
            t = say("Agent", "I see what happened. The autopay attempt on the due date was declined by the bank, so the fee is valid. Updating the card on file will prevent it next time.")
        else:
            t = say("Agent", "That charge is the new streaming add-on that was added on the account last month. It's billed correctly, and you can remove it anytime.")
        say("Customer", "Okay, that makes sense. I didn't realize that.")
        exp.update(q4="Resolved", q4_turn=t)
        rec = ("No promise", 0.0, "Explained charge")
        action = "explained why the charge is valid"
        notes = f"Explained {topic}; charge is valid. Customer understood. No credit offered."
    elif scenario == "refund_processed":
        t = say("Agent", f"I've processed a refund of {money(credit)} to your card. It will show in five to seven business days.")
        say("Customer", "Okay, I'll keep an eye out.")
        exp.update(q1="Yes (firm)", q1_amount=credit, q1_type="Refund", q1_turn=t, q4="Resolved - follow-up pending", q4_turn=t)
        rec = ("Process refund", credit, "Refund issued")
        action = f"processed a {money(credit)} refund"
        notes = f"Confirmed {topic}; processed {money(credit)} refund to card on file. 5-7 business days."
    elif scenario == "callback":
        team = "installation" if reason == "Installation fee" else "billing operations"
        t = say("Agent", f"I need to confirm this with the {team} team before I can explain it. I'll call you back by Thursday with an answer.")
        say("Customer", "Thursday works.")
        exp.update(q4="Resolved - follow-up pending", q4_turn=t)
        rec = ("Call back", 0.0, "Follow-up required")
        action = "scheduled a callback by Thursday"
        notes = f"Reviewed {topic}; needs confirmation from {team} team. Callback scheduled for Thursday. No credit offered."
    elif scenario == "promotion_applied":
        t = say("Agent", f"The promotion dropped off when your plan renewed. I've reapplied the {money(credit)} discount, and it's on the account now.")
        say("Customer", "Thank you, that's what I needed.")
        exp.update(q1="Yes (firm)", q1_amount=credit, q1_type="Promotion", q1_turn=t, q4="Resolved", q4_turn=t)
        rec = ("Apply promotion", credit, "Promotion applied")
        action = f"reapplied a {money(credit)} promotion"
        notes = f"Promotion missing after renewal; reapplied {money(credit)} discount."
    else:  # unresolved
        t = say("Agent", "I'm not able to see why that charge is there, and I don't have a way to change it from my screen. You may want to call back later.")
        say("Customer", "So nothing is happening? That's frustrating.")
        exp.update(q4="Not resolved", q4_turn=t)
        rec = ("No promise", 0.0, "No resolution")
        action = "could not find the cause and took no next step"
        notes = f"Customer called about {topic}. Unable to determine cause. No action taken."

    say("Agent", rng.choice(CLOSE_THANKS))
    say("Customer", rng.choice(CUST_BYE))
    summary = f"Customer called about {topic}. Agent {action}. Outcome: {rec[2].lower()}."
    call = {"call_id": cid, "contact_reason": reason, "promised_action": rec[0],
            "promised_amount": f"{rec[1]:.2f}", "disposition": rec[2], "summary": summary,
            "agent_notes": notes, "turns": turns}
    return call, scenario, exp


def plant(call, scenario, exp, problem):
    if problem == "NOTES_CONTRADICT_CALL":
        call["agent_notes"] = "Customer accepted all charges and reported no billing concern. No action needed."
        exp.update(q3="Contradicts", q3_field="Notes")
    elif problem == "PROMISE_OMITTED_FROM_NOTES":
        topic = REASONS[call["contact_reason"]][1]
        call["agent_notes"] = f"Reviewed account; discussed {topic}."
        exp.update(q3="Incomplete", q3_field="Notes", q3_coaching="Yes")
    elif problem == "RECORD_AMOUNT_MISMATCH":
        real = float(call["promised_amount"])
        call["promised_amount"] = f"{round(real + rng.uniform(5, 40), 2):.2f}"
        exp.update(q3="Contradicts", q3_field="Amount")
    elif problem == "RECORD_SAYS_NO_PROMISE":
        call["promised_action"], call["promised_amount"] = "No promise", "0.00"
        exp.update(q3="Contradicts", q3_field="Promised action")
    elif problem == "RECORD_OVERSTATES_PROMISE":
        call["promised_action"] = "Issue credit"
        exp.update(q3="Contradicts", q3_field="Promised action")
    elif problem == "SUMMARY_SAYS_RESOLVED":
        topic = REASONS[call["contact_reason"]][1]
        call["summary"] = f"Customer called about {topic}. Agent resolved the issue. Outcome: resolved."
        call["disposition"] = "Resolved"
        exp.update(q3="Contradicts", q3_field="Summary")
    elif problem == "NOTES_MISSING":
        call["agent_notes"] = ""
        exp.update(q3="Missing", q3_field="Notes", q3_coaching="Yes")


def make_edge(call, exp):
    """Replace the resolution with a vague, borderline promise."""
    vague = "Let me see what I can do about a credit on that. I'll make a note on the account."
    for k, (who, text) in enumerate(call["turns"]):
        if who == "Agent" and k + 1 == exp["q1_turn"]:
            call["turns"][k] = ("Agent", vague)
            call["turns"][k + 1] = ("Customer", "Okay. I hope something actually happens this time.")
    topic = REASONS[call["contact_reason"]][1]
    call["promised_action"], call["promised_amount"], call["disposition"] = "Investigate", "0.00", "Follow-up required"
    call["summary"] = f"Customer called about {topic}. Agent said they would see what they could do about a credit. Outcome: follow-up required."
    call["agent_notes"] = f"Reviewed {topic}; customer asked about a credit. Agent to look into it."
    exp.update(q1="Yes (conditional)", q1_confidence="Medium", q1_amount="", q1_type="Credit", q4="Resolved - follow-up pending")  # Billy, Nov 11


def main():
    scen_list = [s for s, w in SCENARIO_WEIGHTS.items() for _ in range(w)]
    assert len(scen_list) == N_CALLS
    rng.shuffle(scen_list)
    calls = []
    for n, s in enumerate(scen_list, 1):
        calls.append(build_call(n, s))

    idx = list(range(N_CALLS))
    rng.shuffle(idx)
    problem_names = list(PROBLEMS)
    planted = {}
    for k in idx:
        if len(planted) >= N_PROBLEMS:
            break
        call, scen, exp = calls[k]
        options = [p for p in problem_names if PROBLEMS[p] is None or scen in PROBLEMS[p]]
        counts = {p: sum(1 for v in planted.values() if v == p) for p in options}
        p = min(options, key=lambda x: (counts[x], rng.random()))
        plant(call, scen, exp, p)
        planted[k] = p
    edge_pool = [k for k in idx if k not in planted and calls[k][1] == "conditional_request"]
    edges = set(edge_pool[:N_EDGE])
    for k in edges:
        make_edge(calls[k][0], calls[k][2])

    with open("matched_interactions.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["call_id", "contact_reason", "summary", "agent_notes", "promised_action", "promised_amount", "disposition"])
        for call, _, _ in calls:
            w.writerow([call[x] for x in ["call_id", "contact_reason", "summary", "agent_notes", "promised_action", "promised_amount", "disposition"]])
    with open("matched_transcripts.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["call_id", "turn_number", "speaker", "utterance"])
        for call, _, _ in calls:
            for t, (who, text) in enumerate(call["turns"], 1):
                w.writerow([call["call_id"], t, who, text])
    with open("matched_answer_key.csv", "w", newline="") as f:
        w = csv.writer(f)
        cols = ["q1", "q1_amount", "q1_type", "q1_turn", "q1_confidence", "q2", "q2_asked_credit", "q2_turn", "q3", "q3_field", "q3_coaching", "q4", "q4_turn"]
        w.writerow(["call_id", "scenario", "planted_problem", "edge_case"] + cols)
        for k, (call, scen, exp) in enumerate(calls):
            w.writerow([call["call_id"], scen, planted.get(k, ""), "Yes" if k in edges else ""] + [exp[c] for c in cols])
    return calls, planted, edges


if __name__ == "__main__":
    calls, planted, edges = main()
    from collections import Counter
    print("calls", len(calls), "planted", len(planted), "edge", len(edges))
    print(Counter(planted.values()))
    print(Counter(s for _, s, _ in calls))
