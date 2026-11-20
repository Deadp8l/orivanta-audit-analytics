"""Combine reviews from fresh Claude helper sessions into one predictions file.

Each helper session got only the rubric, the output schema and a batch of 15 calls,
and wrote out_XX.json. This validates every review against the schema's allowed
values, applies the human-review rules in code, and writes
results/claude_helpers_predictions.csv.

Usage: python ai_review/collect_helper_reviews.py <folder with out_*.json>
"""
import glob
import json
import sys

from common import RESULTS, load_calls, write_predictions
from run_claude_review import SCHEMA, flatten


def check(obj, schema, path=""):
    """Small validator for this schema: required keys, no extras, enums, basic types."""
    errs = []
    if "anyOf" in schema:
        if not any(not check(obj, s, path) for s in schema["anyOf"]):
            errs.append(f"{path}: {obj!r} matches no allowed type")
        return errs
    t = schema.get("type")
    if t == "object":
        if not isinstance(obj, dict):
            return [f"{path}: not an object"]
        props = schema["properties"]
        errs += [f"{path}.{k}: missing" for k in schema["required"] if k not in obj]
        errs += [f"{path}.{k}: unexpected" for k in obj if k not in props and k != "call_id"]
        for k, s in props.items():
            if k in obj:
                errs += check(obj[k], s, f"{path}.{k}")
    elif t == "string":
        if not isinstance(obj, str):
            errs.append(f"{path}: not a string")
        elif "enum" in schema and obj not in schema["enum"]:
            errs.append(f"{path}: {obj!r} not allowed")
    elif t == "integer":
        if not isinstance(obj, int) or isinstance(obj, bool):
            errs.append(f"{path}: not an integer")
    elif t == "number":
        if not isinstance(obj, (int, float)) or isinstance(obj, bool):
            errs.append(f"{path}: not a number")
    elif t == "null":
        if obj is not None:
            errs.append(f"{path}: not null")
    return errs


def main(folder):
    expected = {c["call_id"] for c in load_calls()}
    rows, problems, seen = [], [], set()
    for f in sorted(glob.glob(f"{folder}/out_*.json")):
        for r in json.load(open(f)):
            cid = r.get("call_id")
            errs = check(r, SCHEMA, cid or "?")
            if errs:
                problems.append((f, cid, errs))
                continue
            if cid in seen:
                problems.append((f, cid, ["duplicate"]))
                continue
            seen.add(cid)
            rows.append(flatten(cid, r))
    missing = sorted(expected - seen)
    write_predictions(RESULTS / "claude_helpers_predictions.csv", sorted(rows, key=lambda p: p["call_id"]))
    print(f"Valid reviews: {len(rows)}/150")
    print(f"Missing calls: {missing or 'none'}")
    for f, cid, errs in problems:
        print(f"INVALID {cid} in {f}: {errs[:3]}")


if __name__ == "__main__":
    main(sys.argv[1])
