# Orivanta Transcript Review Rubric (v1.3)

Author: Billy Feliciano. All data is synthetic; Orivanta Home Services is a fictional company.

Review one customer-care call. Inputs: the transcript (numbered turns), plus the call record: summary, agent notes, promised action, promised amount and disposition.

## Global rules
- Every answer other than "No" or "Match" must cite the supporting turn number and quote the line.
- If you are unsure, answer "Unclear" and give Low confidence. Never guess.
- Confidence per answer:
  - **High:** a direct quote clearly fits the definition, and nothing in the call conflicts with it.
  - **Medium:** a quote fits, but the wording is vague (for example, "let me see what I can do") or one line points the other way.
  - **Low:** no supporting quote, or the evidence conflicts.

## Q1. Did the agent promise a credit, refund or adjustment?
Answers: Yes (firm) · Yes (conditional) · No · Unclear. Also capture the amount (if stated) and the type (Credit / Refund / Promotion / Other / None).
- **Firm:** the agent says the credit, refund or discount *is applied* or *will be applied*.
- **Conditional:** the agent says they will *request* or *submit* a credit, or starts a process about a credit, refund or adjustment (a follow-up review, request, ticket or escalation), even if they say they can't confirm it yet. The process counts only when the agent ties it to a credit, refund or adjustment (for example, "I've opened a billing review for a possible credit").
- **Not a promise:** a callback, ticket or review only to *explain* or *confirm* a charge is **No**, even if the customer asked for a credit, as long as the agent never connects the follow-up to a credit, refund or adjustment.
- **Vague promise:** "Let me see what I can do about a credit" counts as **Yes (conditional), Medium confidence**.
- **Type:** use the word the agent uses. "Credit" = Credit; "refund" = Refund; "discount" or "promotion" = Promotion. An **adjustment request** (or any other wording) = **Other**.

## Q2. Did the customer dispute a charge or complain?
Answers: Yes · No · Unclear. Also capture what is disputed, and separately whether the customer **asked for a credit** (Yes / No).
- **Yes** when the customer reports a problem or disputes a charge, even politely.

## Q3. Do the agent notes, summary and record fields match the call?
Answers: Match · Incomplete · Contradicts · Missing. Also capture the field at issue (Notes / Summary / Promised action / Amount / None) and the coaching flag.
- **Incomplete:** the notes leave out something important, such as a credit.
- **Contradicts:** the notes, summary or a record field says something the call doesn't support (for example, a different amount, "no promise" when there was one, "resolved" when it wasn't, or notes saying the customer asked for something they didn't).
- **Record fields are claims, not category labels.** A promised action of "Issue credit" (or "Apply credit", "Refund issued") says the credit was given. If the agent only requested, submitted or sent a credit for review, the field overstates the call: **Contradicts**, field = Promised action.
- **The literal reading applies only when a field overstates the call.** A general field that is true but less specific (for example, "Investigate" when the agent submitted an adjustment request or opened a review) is **Match**.
- **Notes must not change what was said.** If the notes restate the call in a way that changes its meaning (for example, the agent said "I can't confirm a credit yet" and the notes say "could not confirm service outage"), that is **Contradicts**, field = Notes. A paraphrase that keeps the same meaning is Match.
- **Vague but harmless wording is Match.** If the notes are vague but still get the outcome right and don't weaken the customer's claim (for example, "Unable to determine cause. No action taken." when the agent couldn't explain a charge and did nothing), answer Match.
- **Missing:** the notes are blank.
- **Coaching = Yes whenever Q3 is not Match** (Incomplete, Contradicts or Missing). Coaching = No when Q3 is Match.

## Q4. Was the customer's issue resolved?
Answers: Resolved · Resolved - follow-up pending · Not resolved · Unclear.
- **Resolved:** the agent took the right next step and the fix is done.
- **Resolved - follow-up pending:** the right step was taken, but the fix comes later.
  - A refund or credit that is processed but has not yet posted (for example, "processed; it will show in 5–7 business days") is **Resolved - follow-up pending**, not Resolved. The fix isn't done until the money reaches the customer.
- **Not resolved:** no fix and no next step.
- **Unclear:** it isn't clear anyone will follow up. A vague promise such as "Let me see what I can do about a credit. I'll make a note on the account." is **Unclear**.

## Human review (applied by code, not by the reviewer)
A call needs human review when any of these is true:
1. any answer has Low confidence (Medium does not trigger review)
2. Q3 = Contradicts
3. Q1 = firm promise over $50
4. Q1 = any promise with no amount stated
5. Q4 = Not resolved or Unclear

The coaching flag alone does not trigger review; it sends the call to the coaching list.

## Change log
- **v1.0:** four questions, definitions and review rules.
- **v1.1:** any process that could lead to a credit is a conditional promise; vague promises are conditional at Medium confidence; only Low confidence triggers review.
- **v1.2 (Nov 11, 2026, after Billy labeled all 150 calls):** coaching = Yes for any Q3 problem, not only Incomplete or Missing; vague promises are Q4 = Unclear; "adjustment request" is Q1 type Other. Billy's labeling also found 5 calls where the generated notes claimed the customer asked for a credit when they hadn't; the answer key was corrected.
- **v1.3 (Nov 16, 2026; Billy's rulings on the four v1.2 gaps):** a refund or credit that is processed but not yet posted is Q4 = Resolved - follow-up pending; a callback or review only to explain or confirm a charge is Q1 = No, even if the customer asked for a credit, unless the agent ties it to a credit; record fields are read literally, so "Issue credit" when the agent only requested a credit is Q3 = Contradicts; notes that change the meaning of what the agent said are Q3 = Contradicts; vague notes that still get the outcome right and don't weaken the customer's claim are Q3 = Match; a general record field that is true but less specific ("Investigate" for an adjustment request) is Q3 = Match, since the literal reading applies only to fields that overstate the call.
