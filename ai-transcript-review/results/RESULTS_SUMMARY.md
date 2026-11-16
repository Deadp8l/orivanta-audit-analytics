# Results: rubric v1.3, 150 synthetic calls (Nov 16, 2026)

Reference labels: Billy's own labels for all 150 calls, manually reviewed by Billy. On Nov 16, Billy changed Q3 on 14 calls from Match to Contradicts after ruling that "Could not confirm [charge]" notes change what the agent said ("I can't confirm a credit yet"). All 17 calls with that wording are now labeled Contradicts.
Claude reviewer: the official script (`ai_review/run_claude_review.py`, Claude Opus 5.5 through the Claude Code login, medium effort). One separate request per call, given only rubric v1.3, the output schema and that call. No tools, no answer key. Human-review routing was applied by code.

## Headline

| Check | Keyword baseline | Claude (v1.3) |
|---|---|---|
| Problems caught (recall) | 23% | **100%** (50 of 50 planted) |
| Precision on flagged problems | 100% | **100%** |
| False alarms on clean calls | 0 | **0** |
| Q1 promise agreement | 100%* | **100%** |
| Q3 notes agreement | 65% | **100%** |
| Q4 resolved agreement | 83% | **100%** |
| Human-review decision agreement | 83% | **100%** |
| Calls sent to human review | 69% | 66% |

\*The baseline's Q1 score is inflated. Its phrases were written knowing this data set's fixed agent wording; real calls vary much more.

## What changed from v1.2 (Billy's rulings)
1. A refund or credit that is processed but not yet posted is Q4 = Resolved - follow-up pending. Fixed all 18 Q4 disagreements.
2. A callback or review only to explain or confirm a charge is Q1 = No, even if the customer asked for a credit, unless the agent ties it to a credit. The first v1.3 run used broader wording ("or the customer asked for one") and got 8 callback calls wrong; the wording was narrowed and the run repeated.
3. Record fields are read literally: "Issue credit" when the agent only requested a credit is Q3 = Contradicts. "Record overstates the promise" is now caught 6 of 6 (was 4 of 6).
4. Notes that change the meaning of what the agent said are Q3 = Contradicts.
5. Vague notes that still get the outcome right and don't weaken the customer's claim are Q3 = Match (for example, "Unable to determine cause. No action taken."). Resolved MC0089 and MC0119.
6. Record fields are read literally only when they overstate the call. A general field that is true but less specific ("Investigate" for an adjustment request) is Q3 = Match. Resolved MC0073, MC0085 and MC0114.

The rubric was run four times on Nov 16 (after rulings 1-4, after narrowing ruling 2, after ruling 5 and after ruling 6). Numbers above are from the fourth run.

## Remaining disagreement (1 call, not a real error)

| Call | Billy | Claude | Note |
|---|---|---|---|
| MC0109 | Contradicts, field = Promised action | Contradicts, field = Notes | Both fields are wrong on this call; Claude named both in its explanation, but the schema holds one field. |

## Limits
- Results vary slightly between runs on borderline calls (3 calls changed between the second and third runs, before ruling 6 settled them).
- The rubric was refined on these same 150 calls, so these numbers measure agreement on the tuning set, not on unseen calls. A fresh, held-out set is needed to measure real accuracy.
- All data is synthetic and generated from templates, so wording repeats far more than in real calls.
- Two-thirds of calls go to human review because the set was built with many planted problems.

---

# Results: rubric v1.2, 150 synthetic calls (Nov 11, 2026)

Reference labels: Billy's own labels for all 150 calls.
Claude reviewer: 10 fresh Claude Opus 5.5 helper sessions (Claude Code), each given only rubric v1.2, the output schema and 15 calls. No tools, no answer key, no prior conversation. Human-review routing was applied by code.

## Headline

| Check | Keyword baseline | Claude |
|---|---|---|
| Problems caught (recall) | 29% | **96%** |
| Precision on flagged problems | 100% | 96% |
| False alarms on clean calls | 0 | 2 |
| Q3 notes agreement | 74% | **97%** |
| Q4 resolved agreement | 83% | 88% |
| Q1 promise agreement | 100%* | 94% |
| Human-review decision agreement | 83% | **96%** |

\*The baseline's Q1 score is inflated. Its phrases were written knowing this data set's fixed agent wording; real calls vary much more.

Planted problems caught by Claude: 48 of 50. All of each type except "record overstates the promise" (4 of 6).

## Where Claude and Billy disagreed (rubric gaps, not random errors)

| Count | Pattern | Billy | Claude | Rubric gap |
|---|---|---|---|---|
| 18 | Refund processed; money arrives in 5–7 business days | Resolved - follow-up pending | Resolved | The rubric doesn't say whether "processed, arrives later" counts as fixed |
| 9 | Agent schedules a callback to *explain* a charge; no credit mentioned | No promise | Conditional promise (7), Unclear (2) | "Any process that could lead to a credit" is too broad; it caught explanation callbacks |
| 2 | Record says "Issue credit"; agent only requested or reviewed | Contradicts | Match | Helpers split on whether "Issue credit" is a category label or a claim |
| 2 | Notes say "could not confirm service outage"; agent said "can't confirm a credit yet" (MC0045, MC0138) | Match | Contradicts | Possibly a real wording mismatch in the generated notes; needs Billy's ruling |

## Next
- Billy rules on the four gaps; publish as rubric v1.3.
- Rerun the official script (`run_claude_review.py`, Claude login) on v1.3 to confirm results are consistent.
