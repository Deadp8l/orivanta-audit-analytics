# Case Study: AI Review of Customer-Care Calls

*Draft, Nov 16, 2026. All data is synthetic. Orivanta Home Services is a fictional company.*

## 1. The problem

When a customer calls about a bill, three things can go wrong after the call ends:

- The agent promises a credit, but the notes don't record it, so the credit never happens.
- The record says more than the agent did. For example, it says "Issue credit" when the agent only sent a request.
- The call is marked resolved when the customer is still waiting.

Auditors catch these by reading calls one at a time, which is slow, so only a small sample gets checked. I wanted to see whether an AI reviewer could read every call, flag the risky ones and send them to a person, while matching how a human auditor would judge them.

## 2. Who it's for

- **Auditors:** a short list of calls that need a human look, each with the quote that triggered it.
- **Team leads:** a coaching list of agents whose notes don't match their calls.
- **Customers:** promised credits that actually get recorded.

## 3. What "good" looks like: the rubric

I wrote a four-question rubric. The reviewer answers every question, cites the turn number and quotes the line it relied on.

| Question | Answers |
|---|---|
| Q1. Did the agent promise a credit, refund or adjustment? | Firm, conditional, no or unclear, plus amount and type |
| Q2. Did the customer dispute a charge or complain? | Yes, no or unclear, plus whether they asked for a credit |
| Q3. Do the notes, summary and record fields match the call? | Match, incomplete, contradicts or missing, plus the field at issue |
| Q4. Was the issue resolved? | Resolved, resolved with follow-up pending, not resolved or unclear |

Each answer also gets a confidence level (high, medium or low). If unsure, the reviewer must answer "Unclear" rather than guess.

**The AI doesn't decide what goes to a person; code does.** A call goes to human review if any answer has low confidence, the notes contradict the call, a firm promise is over $50, a promise has no amount, or the issue isn't resolved. Any notes problem also puts the call on the coaching list.

## 4. The test set

- **150 synthetic calls** across 7 billing reasons, such as duplicate charges, outages and installation fees. Each call has a transcript and a call record.
- **50 planted problems** of 7 types: missing notes, notes that contradict the call, a promise left out of the notes, a wrong amount, a record that overstates the promise, a record that says "no promise" when there was one, and a summary that says "resolved" when it wasn't.
- **8 edge cases** with vague promises, such as "Let me see what I can do about a credit."

**I labeled all 150 calls myself**, without the answer key. My labels are the reference the AI is scored against. Labeling also turned up 5 calls where the generated answer key was wrong: it said the customer asked for a credit when they hadn't. I corrected the key.

## 5. The comparison: keyword rules

To show what AI adds, I first built a simple rules-based reviewer. It looks for fixed phrases such as "I've applied" or "submitting a request" and compares amounts. This is what a team might build before trying AI.

## 6. Results

The AI reviewer is Claude (Opus 5.5). Each call is reviewed in a separate request that contains only the rubric, the output format and that one call. It has no tools and no access to the answer key.

| Check | Keyword rules | Claude, rubric v1.2 | Claude, rubric v1.3 |
|---|---|---|---|
| Planted problems caught | 23% | 96% | **100%** (50 of 50) |
| Flagged calls that really had a problem | 100% | 96% | **100%** |
| False alarms on clean calls | 0 | 2 | **0** |
| Notes check (Q3) agrees with my labels | 65% | 97% | **100%** |
| Resolved check (Q4) agrees with my labels | 83% | 88% | **100%** |
| Human-review decision agrees with my labels | 83% | 96% | **100%** |

The keyword rules miss most problems, because they can't tell whether the notes mean the same thing as the call. Claude catches all 50.

*The v1.2 column was scored on Nov 11, before the label changes described in section 7, and used 10 separate Claude sessions of 15 calls each instead of one request per call. The keyword rules' promise score (100%) is inflated, because I wrote its phrases knowing this data set's fixed wording.*

## 7. What the disagreements taught me

The most useful part was reading every call where Claude and I disagreed. Almost none were random errors. Each one showed a gap in my rubric, which I then had to rule on.

| Gap | What happened | My ruling |
|---|---|---|
| A refund is processed but takes 5–7 days to post | 18 calls. I said "follow-up pending"; Claude said "resolved." | Not resolved until the money reaches the customer. |
| A callback only to *explain* a charge | 9 calls. Claude counted it as a conditional promise. | Not a promise unless the agent ties it to a credit. |
| The record says "Issue credit," but the agent only requested one | Claude said it matched. | Record fields are claims, so this contradicts the call. |
| A record field is true but general ("Investigate" for an adjustment request) | Claude flagged it after the previous ruling. | Match. The literal reading applies only when a field overstates the call. |
| Notes say "could not confirm the fee" when the agent said "can't confirm a credit yet" | Claude flagged it; I had marked it a match. | Contradicts. It changes what was said and weakens the customer's claim. |
| Vague notes, such as "Unable to determine cause. No action taken." | Claude flagged 2 outage calls. | Match. The wording is vague but harmless. |

**The AI also caught my inconsistency.** 17 calls had the "could not confirm" wording. I had labeled 3 as contradicting and 14 as matching. Claude flagged all 17 the same way. Once I ruled on what the rule should be, I relabeled the 14 so all 17 agree. A reviewer that applies the rule the same way every time is part of the value.

**Wording matters.** In my first write-up of the callback ruling, I added "or the customer asked for one." That made Claude count 8 callbacks as promises that I hadn't. Narrowing the wording fixed it.

## 8. Limits

- **Measured on the calls I tuned it on.** I refined the rubric using these same 150 calls, so 100% shows how closely Claude follows my rules, not how accurate it would be on new calls. A fresh set of labeled calls is the real test.
- **Synthetic, template-based data.** Wording repeats far more than in real calls.
- **Small run-to-run variation.** Between two runs with no rubric change, 3 borderline calls changed answers. A later ruling settled them.
- **Heavy review load.** Two-thirds of calls go to human review, because the test set was built with many planted problems.
- **Not a production system.** It's one script on one laptop, about 35 minutes for 150 calls.

## 9. What's next

1. Label a fresh set of calls and run v1.3 on them unchanged, to measure real accuracy.
2. Add harder calls: sarcasm, interruptions, several issues in one call, and agents who correct themselves.
3. Track agreement over time, so any rubric or model change gets re-scored before it's used.

## Files

- `ai_review/rubric.md`: the rubric and its change log
- `ai_review/run_baseline.py`: the keyword-rules reviewer
- `ai_review/run_claude_review.py`: the Claude reviewer
- `ai_review/evaluate.py`: scores either reviewer against my labels
- `results/RESULTS_SUMMARY.md`: full results for each version
