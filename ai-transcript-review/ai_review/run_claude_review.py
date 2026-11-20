"""Claude reviewer: applies rubric v1.3 to each call and returns structured answers.

Usage:
    python ai_review/run_claude_review.py --limit 3     # try a few calls first
    python ai_review/run_claude_review.py               # all 150 calls
    python ai_review/run_claude_review.py --dry-run     # print the prompt for one call, no API call

Default backend (--backend cli) uses your Claude Code login: run `claude auth login` once.
Optional --backend api needs an Anthropic API key in the ANTHROPIC_API_KEY environment variable.
Never put the key in this file or commit it.
"""
import argparse
import json
import sys

from common import RESULTS, ROOT, load_calls, review_flags, transcript_text, write_predictions

MODEL = "claude-opus-5-5"
RUBRIC = (ROOT / "ai_review" / "rubric.md").read_text()

SYSTEM = (
    "You are a careful quality reviewer for a fictional company's customer-care calls. "
    "Apply the rubric below exactly as written. Base every answer only on the transcript and "
    "the call record provided. Quote lines exactly. Do not decide whether the call needs human "
    "review; that is applied separately by code.\n\n" + RUBRIC
)

CONF = {"type": "string", "enum": ["High", "Medium", "Low"]}
TURN = {"anyOf": [{"type": "integer"}, {"type": "null"}]}


def obj(props):
    return {"type": "object", "properties": props, "required": list(props), "additionalProperties": False}


SCHEMA = obj({
    "q1": obj({
        "answer": {"type": "string", "enum": ["Yes (firm)", "Yes (conditional)", "No", "Unclear"]},
        "amount": {"anyOf": [{"type": "number"}, {"type": "null"}]},
        "type": {"type": "string", "enum": ["Credit", "Refund", "Promotion", "Other", "None"]},
        "turn": TURN, "evidence_quote": {"type": "string"}, "confidence": CONF,
    }),
    "q2": obj({
        "answer": {"type": "string", "enum": ["Yes", "No", "Unclear"]},
        "disputed_item": {"type": "string"},
        "customer_asked_for_credit": {"type": "string", "enum": ["Yes", "No"]},
        "turn": TURN, "evidence_quote": {"type": "string"}, "confidence": CONF,
    }),
    "q3": obj({
        "answer": {"type": "string", "enum": ["Match", "Incomplete", "Contradicts", "Missing"]},
        "field_at_issue": {"type": "string", "enum": ["Notes", "Summary", "Promised action", "Amount", "None"]},
        "coaching": {"type": "string", "enum": ["Yes", "No"]},
        "explanation": {"type": "string"}, "confidence": CONF,
    }),
    "q4": obj({
        "answer": {"type": "string", "enum": ["Resolved", "Resolved - follow-up pending", "Not resolved", "Unclear"]},
        "turn": TURN, "evidence_quote": {"type": "string"}, "confidence": CONF,
    }),
    "one_line_summary": {"type": "string"},
})


def user_message(call):
    return (
        f"CALL ID: {call['call_id']}\n"
        f"Contact reason: {call['contact_reason']}\n\n"
        f"TRANSCRIPT\n{transcript_text(call)}\n\n"
        "CALL RECORD\n"
        f"Summary: {call['summary']}\n"
        f"Agent notes: {call['agent_notes'] or '(blank)'}\n"
        f"Promised action: {call['promised_action']}\n"
        f"Promised amount: ${float(call['promised_amount']):,.2f}\n"
        f"Disposition: {call['disposition']}\n\n"
        "Review this call using the rubric."
    )


def review(client, call):
    import anthropic

    response = client.beta.messages.create(
        model=MODEL,
        max_tokens=16000,
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",  # if the model declines, the API retries on a fallback model
        output_config={"effort": "medium", "format": {"type": "json_schema", "schema": SCHEMA}},
        system=[{"type": "text", "text": SYSTEM, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": user_message(call)}],
    )
    if response.stop_reason == "refusal":
        raise RuntimeError(f"{call['call_id']}: model declined ({response.stop_details})")
    if response.stop_reason == "max_tokens":
        raise RuntimeError(f"{call['call_id']}: output cut off at max_tokens")
    if response.model != MODEL:
        print(f"  note: {call['call_id']} was answered by {response.model}, not {MODEL}")
    text = next(b.text for b in response.content if b.type == "text")
    result = json.loads(text)
    result["served_model"] = response.model
    return result, response.usage


def review_cli(call, workdir):
    """Review one call through the Claude Code CLI, using the person's own Claude login.

    Runs in an empty folder with every tool, MCP server and saved session turned off, so
    the reviewer sees only the rubric and this one call (never the answer key).
    """
    import subprocess

    cmd = [
        "claude", "-p", user_message(call),
        "--model", MODEL,
        "--effort", "medium",
        "--system-prompt", SYSTEM,
        "--json-schema", json.dumps(SCHEMA),
        "--output-format", "json",
        "--tools", "",
        "--strict-mcp-config",
        "--no-session-persistence",
    ]
    out = subprocess.run(cmd, cwd=workdir, capture_output=True, text=True, timeout=600)
    try:
        data = json.loads(out.stdout)
    except json.JSONDecodeError:
        raise RuntimeError(f"{call['call_id']}: unexpected CLI output: {(out.stdout or out.stderr)[:300]}")
    if data.get("is_error"):
        raise RuntimeError(f"{call['call_id']}: {data.get('result')}")
    result = data.get("structured_output")
    if result is None:
        result = json.loads(data["result"])
    return result, data.get("usage", {})


def flatten(call_id, r):
    p = {"call_id": call_id, "one_line_summary": r["one_line_summary"]}
    for q in ("q1", "q2", "q3", "q4"):
        for k, v in r[q].items():
            key = f"{q}_{k}" if k != "evidence_quote" else f"{q}_quote"
            p[key] = "" if v is None else v
    p["needs_human_review"], p["review_reasons"] = review_flags(p)
    return p


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None, help="review only the first N calls")
    ap.add_argument("--dry-run", action="store_true", help="print one prompt and exit")
    ap.add_argument("--backend", choices=["cli", "api"], default="cli",
                    help="cli = your Claude login via Claude Code (default); api = ANTHROPIC_API_KEY")
    args = ap.parse_args()

    calls = load_calls()
    if args.limit:
        calls = calls[: args.limit]
    if args.dry_run:
        print(SYSTEM[:600] + "\n...\n\n" + user_message(calls[0]))
        return

    if args.backend == "cli":
        import tempfile

        workdir = tempfile.mkdtemp(prefix="orivanta_review_")
        rows, quotes = [], []
        for i, call in enumerate(calls, 1):
            try:
                r, _ = review_cli(call, workdir)
            except (RuntimeError, json.JSONDecodeError, KeyError) as e:
                print(f"[{i}/{len(calls)}] {call['call_id']} FAILED: {e}")
                if "login" in str(e).lower():
                    sys.exit("Claude Code isn't signed in. Run `claude auth login` in Terminal first.")
                continue
            p = flatten(call["call_id"], r)
            rows.append(p)
            quotes.append({"call_id": call["call_id"], **{f"{q}_quote": r[q].get("evidence_quote", "") for q in ("q1", "q2", "q4")}})
            print(f"[{i}/{len(calls)}] {call['call_id']} Q1={p['q1_answer']} Q3={p['q3_answer']} review={p['needs_human_review']}")
        write_predictions(RESULTS / "claude_predictions.csv", rows)
        with open(RESULTS / "claude_evidence_quotes.json", "w") as f:
            json.dump(quotes, f, indent=1)
        print(f"\nSaved {len(rows)} reviews to results/claude_predictions.csv")
        return

    import anthropic

    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from the environment
    rows, quotes, usage = [], [], {"input": 0, "output": 0, "cache_read": 0}
    served = {}
    for i, call in enumerate(calls, 1):
        try:
            r, u = review(client, call)
        except anthropic.AuthenticationError:
            sys.exit("Authentication failed: set ANTHROPIC_API_KEY to a valid key.")
        except (anthropic.RateLimitError, anthropic.APIConnectionError, anthropic.APIStatusError, RuntimeError, json.JSONDecodeError) as e:
            print(f"[{i}/{len(calls)}] {call['call_id']} FAILED: {e}")
            continue
        model = r.pop("served_model")
        served[model] = served.get(model, 0) + 1
        usage["input"] += u.input_tokens
        usage["output"] += u.output_tokens
        usage["cache_read"] += u.cache_read_input_tokens or 0
        p = flatten(call["call_id"], r)
        rows.append(p)
        quotes.append({"call_id": call["call_id"], **{f"{q}_quote": r[q].get("evidence_quote", "") for q in ("q1", "q2", "q4")}})
        print(f"[{i}/{len(calls)}] {call['call_id']} Q1={p['q1_answer']} Q3={p['q3_answer']} review={p['needs_human_review']}")

    write_predictions(RESULTS / "claude_predictions.csv", rows)
    with open(RESULTS / "claude_evidence_quotes.json", "w") as f:
        json.dump(quotes, f, indent=1)
    print(f"\nSaved {len(rows)} reviews to results/claude_predictions.csv")
    print(f"Tokens: {usage['input']:,} input, {usage['output']:,} output, {usage['cache_read']:,} read from cache")
    print("Models that answered: " + ", ".join(f"{m} ({n} calls)" for m, n in served.items()))


if __name__ == "__main__":
    main()
