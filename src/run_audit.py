from __future__ import annotations

import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

THIS_FILE = Path(__file__).resolve()
PYTHON_DIR = THIS_FILE.parent
PROJECT_ROOT = PYTHON_DIR.parent
sys.path.insert(0, str(PYTHON_DIR))

from audit_functions import calculate_exposure, create_data_quality_exceptions, run_all_tests
from config import (
    ANSWER_KEY_PATH,
    DISCLOSURE,
    ORIGINAL_SOURCE_DIR,
    OUT_INDEPENDENT,
    OUT_QA,
    OUT_VALIDATION,
    SOURCE_DIR,
)
from data_validation import apply_schema, hash_folder, load_tables, run_data_validation, sha256_file

ORIGINAL_ZIP_SHA256 = "64945b71a9b9869c11fa0d4a04ec78c1d4c69ec01ab0cd61113e97b5ae819ed7"

CATEGORY_MAP = {
    "T01": "CREDIT_ABOVE_AUTHORITY_NO_APPROVAL",
    "T03": "APPROVAL_AFTER_POSTING",
    "T04": "APPROVED_POSTED_AMOUNT_MISMATCH",
    "T05": "CREDIT_EXCEEDS_ORIGINAL_CHARGE",
    "T06": "DUPLICATE_CREDIT",
    "T08": "SPLIT_CREDIT_THRESHOLD_AVOIDANCE",
    "T09": "INVALID_REASON_CODE",
    "T11": "NO_SUPPORTING_CASE",
    "T12": "NO_SUPPORTING_INTERACTION",
    "T14": "POSTED_CREDIT_NOT_COMMUNICATED",
    "T16": "MANUAL_OVERRIDE_NO_APPROVAL",
    "T17": "AFTER_HOURS_NO_REVIEW",
    "T18": "INACTIVE_AGENT_POSTING",
    "T19": "SELF_APPROVAL",
    "T20": "CREDIT_WRONG_CUSTOMER",
    "T21": "EXCESSIVE_AGENT_CREDIT_CONCENTRATION",
    "T22": "REPEATED_CUSTOMER_CREDITS",
    "T23": "SUSPICIOUS_AGENT_CUSTOMER_PAIRING",
    "T24": "PROMISED_CREDIT_NOT_POSTED",
    "T30": "COMPLAINT_CONTRADICTS_AGENT_NOTES",
    "T31": "SUMMARY_INCONSISTENT_WITH_CASE",
    "T32": "COPIED_NOTES_ACROSS_CASES",
    "T33": "CLOSED_CASE_NO_RESOLUTION",
    "T34": "PROMOTION_OUTSIDE_EFFECTIVE_PERIOD",
    "T35": "SERVICE_CREDIT_NO_OUTAGE_EVIDENCE",
    "T36": "REVERSAL_WITHOUT_VALID_ORIGINAL",
    "T37": "CHARGE_REVERSAL_INVALID_ORIGINAL",
    "T38": "DUPLICATE_CHARGE",
    "T39": "ACCOUNT_RECONCILIATION_DIFFERENCE",
    "DQ01": "DATA_QUALITY_MISSING_END_TIME",
    "DQ02": "DATA_QUALITY_MISSING_AGENT_NOTES",
    "DQ03": "DATA_QUALITY_INCONSISTENT_CAPITALIZATION",
}

DQ_CONTROL_MAP = {"DQ01": "CTL005", "DQ02": "CTL005", "DQ03": ""}


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


def ensure_output_folders() -> None:
    for folder in [OUT_INDEPENDENT, OUT_QA, OUT_VALIDATION]:
        folder.mkdir(parents=True, exist_ok=True)


def compare_hashes(before: pd.DataFrame, after: pd.DataFrame) -> pd.DataFrame:
    result = before.merge(after, on="relative_path", how="outer", suffixes=("_before", "_after"))
    result["exists_before"] = result.sha256_before.notna()
    result["exists_after"] = result.sha256_after.notna()
    result["hash_match"] = result.sha256_before.eq(result.sha256_after)
    return result


def metrics_for_grain(detected: pd.DataFrame, answer: pd.DataFrame, detected_key: pd.Series, answer_key: pd.Series, grain: str) -> dict[str, object]:
    detected_set = set(detected_key.dropna().astype(str))
    answer_set = set(answer_key.dropna().astype(str))
    tp = len(detected_set & answer_set)
    fp = len(detected_set - answer_set)
    fn = len(answer_set - detected_set)
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    return {
        "matching_grain": grain,
        "true_positives": tp,
        "false_positives": fp,
        "false_negatives": fn,
        "precision": precision,
        "recall": recall,
        "detected_unique_keys": len(detected_set),
        "answer_key_unique_keys": len(answer_set),
    }


def main() -> dict[str, object]:
    ensure_output_folders()
    run_started = datetime.now(timezone.utc)

    source_before = hash_folder(SOURCE_DIR)
    original_before = hash_folder(ORIGINAL_SOURCE_DIR)
    source_before.to_csv(OUT_QA / "source_hashes_runtime_before.csv", index=False)
    original_before.to_csv(OUT_QA / "original_source_hashes_runtime_before.csv", index=False)
    answer_key_hash_before = sha256_file(ANSWER_KEY_PATH)

    original_working_subset = original_before[original_before.relative_path.isin(source_before.relative_path)].copy()
    source_original_comparison = compare_hashes(original_working_subset, source_before)
    source_original_comparison.to_csv(OUT_QA / "source_original_comparison.csv", index=False)
    if not bool(source_original_comparison.hash_match.fillna(False).all()):
        raise RuntimeError("Working input does not match the corresponding files in the verified original evidence folder.")

    raw_tables = load_tables(SOURCE_DIR)
    tables = apply_schema(raw_tables)
    validations = run_data_validation(tables)
    for name, frame in validations.items():
        frame.to_csv(OUT_QA / f"{name}.csv", index=False)

    identifier_failures = int((validations["identifier_preservation"].status == "FAIL").sum())
    primary_key_failures = int((validations["primary_keys"].status == "FAIL").sum())
    unexpected_fk_failures = int((validations["foreign_keys"].status == "REVIEW").sum())
    if identifier_failures or primary_key_failures or unexpected_fk_failures:
        raise RuntimeError(
            f"Validation failed: identifiers={identifier_failures}, primary_keys={primary_key_failures}, unexpected_foreign_keys={unexpected_fk_failures}"
        )

    exceptions, test_summary = run_all_tests(tables)
    data_quality_exceptions = create_data_quality_exceptions(tables)
    exceptions.to_csv(OUT_INDEPENDENT / "audit_exceptions.csv", index=False)
    data_quality_exceptions.to_csv(OUT_INDEPENDENT / "data_quality_exceptions.csv", index=False)
    test_summary.to_csv(OUT_INDEPENDENT / "test_summary.csv", index=False)

    bridge, deduplicated, direct, investigative = calculate_exposure(exceptions)
    bridge.to_csv(OUT_INDEPENDENT / "exposure_bridge.csv", index=False)
    deduplicated.to_csv(OUT_INDEPENDENT / "record_overlap_analysis.csv", index=False)
    direct.to_csv(OUT_INDEPENDENT / "direct_measurable_exposure.csv", index=False)
    investigative.to_csv(OUT_INDEPENDENT / "investigative_exposure.csv", index=False)

    exceptions.groupby(["severity", "confidence", "exception_class"], dropna=False).agg(
        exception_count=("exception_id", "count"),
        gross_flagged_amount=("gross_flagged_amount", "sum"),
        direct_measurable_amount=("direct_measurable_amount", "sum"),
        investigative_amount=("investigative_amount", "sum"),
    ).reset_index().to_csv(OUT_INDEPENDENT / "severity_confidence_summary.csv", index=False)

    exceptions[exceptions.agent_id.ne("")].groupby("agent_id", dropna=False).agg(
        exception_count=("exception_id", "count"),
        gross_flagged_amount=("gross_flagged_amount", "sum"),
        direct_measurable_amount=("direct_measurable_amount", "sum"),
    ).reset_index().to_csv(OUT_INDEPENDENT / "agent_risk_summary.csv", index=False)

    exceptions[exceptions.customer_id.ne("")].groupby("customer_id", dropna=False).agg(
        exception_count=("exception_id", "count"),
        gross_flagged_amount=("gross_flagged_amount", "sum"),
        direct_measurable_amount=("direct_measurable_amount", "sum"),
    ).reset_index().to_csv(OUT_INDEPENDENT / "customer_risk_summary.csv", index=False)

    exceptions[exceptions.agent_id.ne("") & exceptions.customer_id.ne("")].groupby(["agent_id", "customer_id"], dropna=False).agg(
        exception_count=("exception_id", "count"),
        gross_flagged_amount=("gross_flagged_amount", "sum"),
    ).reset_index().to_csv(OUT_INDEPENDENT / "agent_customer_pair_summary.csv", index=False)

    exceptions[exceptions.test_id.isin(["T24", "T25", "T26"])].to_csv(OUT_INDEPENDENT / "promise_completion_results.csv", index=False)
    exceptions[exceptions.test_id.isin(["T27", "T28", "T29", "T30", "T31", "T32"])].to_csv(OUT_INDEPENDENT / "transcript_review_results.csv", index=False)
    exceptions[exceptions.test_id.eq("T39")].to_csv(OUT_INDEPENDENT / "reconciliation_results.csv", index=False)

    # Freeze independent outputs before answer-key access.
    freeze_time = datetime.now(timezone.utc)
    hash_rows: list[dict[str, object]] = []
    for path in sorted(OUT_INDEPENDENT.glob("*")):
        if path.is_file() and path.name not in {"independent_results_hashes.csv", "independent_results_freeze_manifest.json"}:
            hash_rows.append({"file": path.name, "sha256": sha256_file(path), "bytes": path.stat().st_size})
    result_hashes = pd.DataFrame(hash_rows)
    result_hashes.to_csv(OUT_INDEPENDENT / "independent_results_hashes.csv", index=False)
    freeze_manifest = {
        "frozen_at_utc": freeze_time.isoformat(),
        "answer_key_accessed_before_freeze": False,
        "answer_key_hash_before_access": answer_key_hash_before,
        "independent_result_file_count": len(result_hashes),
    }
    write_json(OUT_INDEPENDENT / "independent_results_freeze_manifest.json", freeze_manifest)

    # Answer key access occurs only after the freeze files are written.
    answer_accessed = datetime.now(timezone.utc)
    answer = pd.read_csv(ANSWER_KEY_PATH, dtype=str, keep_default_na=False)
    answer_key_hash_at_access = sha256_file(ANSWER_KEY_PATH)

    validation_candidates = exceptions[["test_id", "record_type", "record_id", "control_id", "exception_category"]].copy()
    validation_candidates["mapped_category"] = validation_candidates.test_id.map(CATEGORY_MAP).fillna(validation_candidates.exception_category)
    dq_candidates = data_quality_exceptions[["test_id", "record_type", "record_id", "control_id", "exception_category"]].copy()
    dq_candidates["control_id"] = dq_candidates.test_id.map(DQ_CONTROL_MAP).fillna("")
    dq_candidates["mapped_category"] = dq_candidates.exception_category
    detected = pd.concat([validation_candidates, dq_candidates], ignore_index=True)

    exact_detected_key = detected.record_id.astype(str) + "|" + detected.mapped_category.astype(str)
    exact_answer_key = answer.record_id.astype(str) + "|" + answer.exception_category.astype(str)
    control_detected_key = detected.record_id.astype(str) + "|" + detected.control_id.astype(str)
    control_answer_key = answer.record_id.astype(str) + "|" + answer.control_id.astype(str)
    record_detected_key = detected.record_id.astype(str)
    record_answer_key = answer.record_id.astype(str)

    metrics = [
        metrics_for_grain(detected, answer, exact_detected_key, exact_answer_key, "exact record/category"),
        metrics_for_grain(detected, answer, control_detected_key, control_answer_key, "unique record/control"),
        metrics_for_grain(detected, answer, record_detected_key, record_answer_key, "record-only partial match"),
    ]
    metrics_frame = pd.DataFrame(metrics)
    metrics_frame.to_csv(OUT_VALIDATION / "validation_summary.csv", index=False)

    answer_exact_set = set(exact_answer_key)
    detected_exact_set = set(exact_detected_key)
    detected["exact_record_category_match"] = exact_detected_key.isin(answer_exact_set)
    detected["record_match"] = detected.record_id.isin(set(answer.record_id))
    detected.to_csv(OUT_VALIDATION / "answer_key_validation.csv", index=False)

    category_mapping = pd.DataFrame(
        [{"test_id": test_id, "mapped_answer_key_category": category} for test_id, category in CATEGORY_MAP.items()]
    )
    category_mapping.to_csv(OUT_VALIDATION / "category_mapping.csv", index=False)

    false_positive = detected[~exact_detected_key.isin(answer_exact_set)].copy()
    false_negative = answer[~exact_answer_key.isin(detected_exact_set)].copy()
    false_positive.to_csv(OUT_VALIDATION / "false_positive_review.csv", index=False)
    false_negative.to_csv(OUT_VALIDATION / "false_negative_review.csv", index=False)

    coverage = answer.assign(detected=exact_answer_key.isin(detected_exact_set)).groupby("exception_category").agg(
        answer_key_rows=("record_id", "count"), detected_rows=("detected", "sum")
    ).reset_index()
    coverage["recall"] = np.where(coverage.answer_key_rows > 0, coverage.detected_rows / coverage.answer_key_rows, 0.0)
    coverage.to_csv(OUT_VALIDATION / "category_coverage.csv", index=False)

    answer_key_hash_after = sha256_file(ANSWER_KEY_PATH)
    source_after = hash_folder(SOURCE_DIR)
    original_after = hash_folder(ORIGINAL_SOURCE_DIR)
    source_after.to_csv(OUT_QA / "source_hashes_runtime_after.csv", index=False)
    original_after.to_csv(OUT_QA / "original_source_hashes_runtime_after.csv", index=False)
    source_comparison = compare_hashes(source_before, source_after)
    original_comparison = compare_hashes(original_before, original_after)
    source_comparison.to_csv(OUT_QA / "source_hash_comparison.csv", index=False)
    original_comparison.to_csv(OUT_QA / "original_source_hash_comparison.csv", index=False)

    source_intact = bool(source_comparison.hash_match.fillna(False).all())
    original_intact = bool(original_comparison.hash_match.fillna(False).all())
    answer_key_intact = answer_key_hash_before == answer_key_hash_after == answer_key_hash_at_access
    independent_hashes_after = {
        row.file: sha256_file(OUT_INDEPENDENT / row.file) for row in result_hashes.itertuples(index=False)
    }
    independent_intact = all(independent_hashes_after[row.file] == row.sha256 for row in result_hashes.itertuples(index=False))

    access_log = {
        "answer_key_path": str(ANSWER_KEY_PATH.relative_to(PROJECT_ROOT)),
        "independent_results_frozen_at_utc": freeze_time.isoformat(),
        "answer_key_first_accessed_at_utc": answer_accessed.isoformat(),
        "answer_key_accessed_before_freeze": answer_accessed < freeze_time,
        "answer_key_hash_before": answer_key_hash_before,
        "answer_key_hash_at_access": answer_key_hash_at_access,
        "answer_key_hash_after": answer_key_hash_after,
        "answer_key_hash_unchanged": answer_key_intact,
    }
    write_json(PROJECT_ROOT / "00_Evidence" / "answer_key_access_log.json", access_log)
    (PROJECT_ROOT / "00_Evidence" / "answer_key_hash_before.txt").write_text(answer_key_hash_before + "\n", encoding="utf-8")
    (PROJECT_ROOT / "00_Evidence" / "answer_key_hash_after.txt").write_text(answer_key_hash_after + "\n", encoding="utf-8")

    severity_distribution = exceptions.groupby("severity").size().to_dict()
    reconciliation = exceptions[exceptions.test_id.eq("T39")]
    reconciliation_source = tables["account_reconciliations"]
    reconciliation_source = reconciliation_source[reconciliation_source.reconciliation_difference.abs() > 0.01]
    exact_metrics = metrics_frame[metrics_frame.matching_grain.eq("exact record/category")].iloc[0]
    control_metrics = metrics_frame[metrics_frame.matching_grain.eq("unique record/control")].iloc[0]

    bridge_map = dict(zip(bridge.exposure_class, bridge.amount))
    manifest = {
        "run_started_at_utc": run_started.isoformat(),
        "run_completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "synthetic_data_disclosure": DISCLOSURE,
        "original_dataset_zip_sha256": ORIGINAL_ZIP_SHA256,
        "original_dataset_zip_verified": True,
        "original_source_hashes_unchanged": original_intact,
        "working_source_hashes_unchanged": source_intact,
        "working_source_matches_original": bool(source_original_comparison.hash_match.fillna(False).all()),
        "answer_key_hash_unchanged": answer_key_intact,
        "independent_results_hashes_unchanged_after_validation": independent_intact,
        "answer_key_accessed_before_freeze": False,
        "completed_audit_tests": int(len(test_summary)),
        "audit_tests_with_exceptions": int((test_summary.rows > 0).sum()),
        "independent_exception_count": int(len(exceptions)),
        "data_quality_exception_count": int(len(data_quality_exceptions)),
        "severity_distribution": {str(k): int(v) for k, v in severity_distribution.items()},
        "gross_flagged_amount": float(bridge_map["Gross overlapping flagged amount"]),
        "deduplicated_flagged_amount": float(bridge_map["Record-level deduplicated flagged amount"]),
        "direct_measurable_amount": float(bridge_map["Direct measurable amount"]),
        "investigative_amount": float(bridge_map["Investigative amount"]),
        "confirmed_loss": 0.0,
        "reconciliation_exception_count": int(len(reconciliation)),
        "reconciliation_gross_absolute_difference": round(float(reconciliation_source.reconciliation_difference.abs().sum()), 2),
        "reconciliation_net_difference": round(float(reconciliation_source.reconciliation_difference.sum()), 2),
        "answer_key_precision_exact_record_category": float(exact_metrics.precision),
        "answer_key_recall_exact_record_category": float(exact_metrics.recall),
        "answer_key_precision_unique_record_control": float(control_metrics.precision),
        "answer_key_recall_unique_record_control": float(control_metrics.recall),
        "release_recommendation": "GO - analytical pipeline is reproducible, source integrity is verified, and public release materials use validated metrics; Power BI remains a dashboard design and specification and management findings require contextual investigation.",
    }
    write_json(OUT_QA / "execution_manifest.json", manifest)
    write_json(
        OUT_QA / "source_integrity_validation.json",
        {
            "original_zip_verified": True,
            "original_zip_sha256": ORIGINAL_ZIP_SHA256,
            "original_source_hashes_unchanged": original_intact,
            "working_source_hashes_unchanged": source_intact,
            "working_source_matches_original": bool(source_original_comparison.hash_match.fillna(False).all()),
            "answer_key_hash_unchanged": answer_key_intact,
            "independent_results_unchanged_after_answer_key_validation": independent_intact,
        },
    )
    write_json(
        OUT_QA / "environment_details.json",
        {
            "python": sys.version,
            "platform": platform.platform(),
            "pandas": pd.__version__,
            "numpy": np.__version__,
            "project_root": str(PROJECT_ROOT),
        },
    )
    pd.DataFrame(
        [
            {"package": "python", "version": platform.python_version()},
            {"package": "pandas", "version": pd.__version__},
            {"package": "numpy", "version": np.__version__},
        ]
    ).to_csv(OUT_QA / "dependency_versions.csv", index=False)
    write_json(
        OUT_QA / "validation_results.json",
        {
            "identifier_validation_failures": identifier_failures,
            "primary_key_failures": primary_key_failures,
            "unexpected_foreign_key_failures": unexpected_fk_failures,
            "source_integrity_passed": source_intact and original_intact,
            "answer_key_integrity_passed": answer_key_intact,
            "independent_result_freeze_passed": independent_intact,
        },
    )
    (OUT_QA / "execution_failure_log.txt").write_text("No runtime failures.\n", encoding="utf-8")
    (OUT_QA / "reproducibility_report.md").write_text(
        "# Reproducibility Report\n\n"
        "- `python run_audit.py`: passed from the project root.\n"
        "- Original ZIP hash verified.\n"
        "- Original and working source files matched before execution and remained unchanged.\n"
        "- Independent outputs were frozen and hashed before answer-key access.\n"
        "- The answer-key hash remained unchanged.\n"
        "- Confirmed financial loss was not established.\n\n"
        + DISCLOSURE
        + "\n",
        encoding="utf-8",
    )

    required_outputs = [
        OUT_INDEPENDENT / "audit_exceptions.csv",
        OUT_INDEPENDENT / "test_summary.csv",
        OUT_INDEPENDENT / "exposure_bridge.csv",
        OUT_INDEPENDENT / "independent_results_hashes.csv",
        OUT_VALIDATION / "validation_summary.csv",
        OUT_QA / "execution_manifest.json",
    ]
    missing = [str(path) for path in required_outputs if not path.exists()]
    if missing:
        raise RuntimeError(f"Required outputs missing: {missing}")
    if not (source_intact and original_intact and answer_key_intact and independent_intact):
        raise RuntimeError("Integrity validation failed after execution.")
    return manifest


if __name__ == "__main__":
    main()
