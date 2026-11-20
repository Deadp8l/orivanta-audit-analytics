# Sample Output: One Call, End to End

*Synthetic data. Orivanta Home Services is a fictional company.*

This is call **MC0029**, copied from `data/` and `results/` (rubric v1.3 run). It has a planted problem: the record says more than the agent did. The keyword rules missed it; Claude caught it, and its answers match my labels.

## The call

| Turn | Speaker | Line |
|---|---|---|
| 1 | Agent | Thanks for contacting Orivanta. I can help with account and billing questions. |
| 2 | Customer | My service was out for two days and I'm still billed $90.15 for the month. |
| 3 | Agent | I understand. Give me a moment to open the billing history. |
| 4 | Agent | I'm looking at the entries now and checking where that amount came from. |
| 5 | Agent | I can't apply it myself, but I'm submitting a $18.03 adjustment request to billing now. You'll get an email once it's reviewed, usually within five business days. |
| 6 | Customer | Okay. I'll watch for the email. |
| 7 | Agent | Is there anything else I can help with today? |
| 8 | Customer | No, that's all. Thank you. |

## The call record

| Field | Value |
|---|---|
| Summary | Customer called about service outage. Agent submitted a $18.03 adjustment request. Outcome: credit requested. |
| Agent notes | Reviewed service outage; submitted $18.03 adjustment request to billing for approval. Customer told to expect an email in 5 business days. |
| Promised action | **Issue credit** |
| Promised amount | $18.03 |
| Disposition | Credit requested |

## Claude's answers

| Question | Answer | Confidence | Evidence |
|---|---|---|---|
| Q1. Promise? | Yes (conditional), $18.03, type Other | High | Turn 5: "I can't apply it myself, but I'm submitting a $18.03 adjustment request to billing now." |
| Q2. Complaint? | Yes: full monthly charge despite a two-day outage | High | Turn 2: "My service was out for two days and I'm still billed $90.15 for the month." |
| Q3. Record matches call? | **Contradicts**, field = Promised action, coaching = Yes | High | See explanation below |
| Q4. Resolved? | Resolved - follow-up pending | High | Turn 5: "You'll get an email once it's reviewed, usually within five business days." |

**Q3 explanation (Claude's words):** "The promised action field says "Issue credit," which means the credit was given. In turn 5 the agent only submitted a $18.03 adjustment request for review and said "I can't apply it myself." Read literally, the field overstates the call. The notes, summary, amount and disposition are otherwise accurate."

## What happens next (applied by code, not by the AI)

| | Keyword rules | Claude |
|---|---|---|
| Q3 notes check | Match (missed) | Contradicts |
| Sent to human review | No | **Yes**: Q3 contradicts |
| Coaching list | No | Yes |

The keyword rules check phrases and amounts, and every phrase and amount here is consistent. The problem is meaning: "Issue credit" claims something the agent didn't do. This is the rubric v1.3 ruling that record fields are claims, not category labels.
