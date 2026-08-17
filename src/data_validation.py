from __future__ import annotations

import hashlib
import zipfile
from pathlib import Path
from typing import Dict

import numpy as np
import pandas as pd

from schemas import (
    BOOLEAN_COLUMNS,
    DATE_COLUMNS,
    IDENTIFIER_COLUMNS,
    INTEGER_COLUMNS,
    MONETARY_COLUMNS,
    PRIMARY_KEYS,
    SOURCE_TABLES,
)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def hash_folder(folder: Path) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    if folder.is_file() and folder.suffix.lower() == ".zip":
        with zipfile.ZipFile(folder) as zf:
            for info in sorted(zf.infolist(), key=lambda i: i.filename):
                if info.is_dir():
                    continue
                data = zf.read(info.filename)
                rows.append({
                    "relative_path": info.filename,
                    "bytes": len(data),
                    "sha256": hashlib.sha256(data).hexdigest(),
                })
        return pd.DataFrame(rows)
    for path in sorted(folder.rglob("*")):
        if path.is_file():
            rows.append(
                {
                    "relative_path": str(path.relative_to(folder)),
                    "bytes": path.stat().st_size,
                    "sha256": sha256_file(path),
                }
            )
    return pd.DataFrame(rows)


def load_tables(source_dir: Path) -> Dict[str, pd.DataFrame]:
    tables: Dict[str, pd.DataFrame] = {}
    if source_dir.is_file() and source_dir.suffix.lower() == ".zip":
        with zipfile.ZipFile(source_dir) as zf:
            names = set(zf.namelist())
            for table_name in SOURCE_TABLES:
                member = f"{table_name}.csv"
                if member not in names:
                    raise FileNotFoundError(f"Required source file is missing from zip: {member}")
                with zf.open(member) as file:
                    tables[table_name] = pd.read_csv(file, dtype=str, keep_default_na=False)
        return tables
    for table_name in SOURCE_TABLES:
        path = source_dir / f"{table_name}.csv"
        if not path.exists():
            raise FileNotFoundError(f"Required source file is missing: {path}")
        tables[table_name] = pd.read_csv(path, dtype=str, keep_default_na=False)
    return tables


def apply_schema(tables: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
    result: Dict[str, pd.DataFrame] = {}
    for table_name, frame in tables.items():
        df = frame.copy()
        for column in df.columns:
            if column.endswith("_id") or column in IDENTIFIER_COLUMNS:
                df[column] = df[column].astype("string")
            elif column in MONETARY_COLUMNS:
                df[column] = pd.to_numeric(df[column], errors="coerce").round(2)
            elif column in INTEGER_COLUMNS:
                df[column] = pd.to_numeric(df[column], errors="coerce").astype("Int64")
            elif column in BOOLEAN_COLUMNS:
                df[column] = pd.to_numeric(df[column], errors="coerce").astype("Int64")
            elif column in DATE_COLUMNS:
                df[column] = pd.to_datetime(df[column], errors="coerce")
        result[table_name] = df
    return result


def validate_identifier_columns(tables: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for table_name, df in tables.items():
        for column in df.columns:
            if column.endswith("_id") or column in IDENTIFIER_COLUMNS:
                values = df[column].astype("string")
                literal_nan = int(values.str.lower().eq("nan").sum())
                numeric_dtype = pd.api.types.is_numeric_dtype(df[column])
                rows.append(
                    {
                        "table": table_name,
                        "column": column,
                        "dtype": str(df[column].dtype),
                        "literal_nan_count": literal_nan,
                        "blank_count": int(values.eq("").sum()),
                        "numeric_dtype": bool(numeric_dtype),
                        "status": "PASS" if literal_nan == 0 and not numeric_dtype else "FAIL",
                    }
                )
    return pd.DataFrame(rows)


def validate_primary_keys(tables: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for table_name, primary_key in PRIMARY_KEYS.items():
        df = tables[table_name]
        values = df[primary_key].astype("string")
        blank = int(values.eq("").sum())
        duplicate = int(values.duplicated().sum())
        rows.append(
            {
                "table": table_name,
                "primary_key": primary_key,
                "rows": len(df),
                "blank_keys": blank,
                "duplicate_keys": duplicate,
                "status": "PASS" if blank == 0 and duplicate == 0 else "FAIL",
            }
        )
    transcripts = tables["transcripts"]
    transcript_blank = int(transcripts["transcript_id"].astype("string").eq("").sum() + transcripts["turn_number"].isna().sum())
    transcript_duplicate = int(transcripts.duplicated(["transcript_id", "turn_number"]).sum())
    rows.append({
        "table": "transcripts",
        "primary_key": "transcript_id + turn_number",
        "rows": len(transcripts),
        "blank_keys": transcript_blank,
        "duplicate_keys": transcript_duplicate,
        "status": "PASS" if transcript_blank == 0 and transcript_duplicate == 0 else "FAIL",
    })
    return pd.DataFrame(rows)


def validate_foreign_keys(tables: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    foreign_keys = {
        "accounts": {
            "customer_id": ("customers", "customer_id"),
            "service_plan_id": ("products_services", "product_service_id"),
        },
        "charges": {
            "account_id": ("accounts", "account_id"),
            "customer_id": ("customers", "customer_id"),
            "product_service_id": ("products_services", "product_service_id"),
            "created_by_agent_id": ("agents", "agent_id"),
            "location_id": ("locations", "location_id"),
            "original_charge_id": ("charges", "charge_id"),
        },
        "credits_adjustments": {
            "account_id": ("accounts", "account_id"),
            "customer_id": ("customers", "customer_id"),
            "original_charge_id": ("charges", "charge_id"),
            "case_id": ("cases_disputes", "case_id"),
            "interaction_id": ("interactions", "interaction_id"),
            "agent_id": ("agents", "agent_id"),
            "supervisor_id": ("supervisors", "supervisor_id"),
            "approval_id": ("approvals", "approval_id"),
            "reason_code": ("reason_codes", "reason_code"),
        },
        "payments": {
            "account_id": ("accounts", "account_id"),
            "customer_id": ("customers", "customer_id"),
            "original_payment_id": ("payments", "payment_id"),
        },
        "cases_disputes": {
            "account_id": ("accounts", "account_id"),
            "customer_id": ("customers", "customer_id"),
            "disputed_charge_id": ("charges", "charge_id"),
            "assigned_agent_id": ("agents", "agent_id"),
            "assigned_supervisor_id": ("supervisors", "supervisor_id"),
        },
        "interactions": {
            "case_id": ("cases_disputes", "case_id"),
            "account_id": ("accounts", "account_id"),
            "customer_id": ("customers", "customer_id"),
            "agent_id": ("agents", "agent_id"),
        },
        "transcripts": {
            "interaction_id": ("interactions", "interaction_id"),
            "case_id": ("cases_disputes", "case_id"),
            "account_id": ("accounts", "account_id"),
            "customer_id": ("customers", "customer_id"),
            "agent_id": ("agents", "agent_id"),
        },
        "approvals": {
            "credit_id": ("credits_adjustments", "credit_id"),
            "agent_id": ("agents", "agent_id"),
            "supervisor_id": ("supervisors", "supervisor_id"),
        },
        "account_reconciliations": {
            "account_id": ("accounts", "account_id"),
            "customer_id": ("customers", "customer_id"),
        },
    }
    expected_seeded = {
        ("credits_adjustments", "supervisor_id"),
        ("approvals", "supervisor_id"),
        ("credits_adjustments", "reason_code"),
        ("payments", "original_payment_id"),
        ("charges", "original_charge_id"),
    }
    rows: list[dict[str, object]] = []
    for child_table, mappings in foreign_keys.items():
        child = tables[child_table]
        for child_field, (parent_table, parent_field) in mappings.items():
            nonblank = child.loc[child[child_field].astype("string").ne(""), child_field].astype("string")
            valid = set(tables[parent_table][parent_field].astype("string"))
            invalid = nonblank[~nonblank.isin(valid)]
            seeded = (child_table, child_field) in expected_seeded
            status = "EXPECTED_SEEDED_REVIEW" if len(invalid) and seeded else ("PASS" if len(invalid) == 0 else "REVIEW")
            rows.append(
                {
                    "child_table": child_table,
                    "child_field": child_field,
                    "parent_table": parent_table,
                    "parent_field": parent_field,
                    "nonblank_values": len(nonblank),
                    "invalid_references": len(invalid),
                    "sample_invalid": "; ".join(sorted(invalid.unique())[:10]),
                    "expected_seeded_issue": seeded,
                    "status": status,
                }
            )
    return pd.DataFrame(rows)


def validate_dates_amounts(tables: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for table_name, df in tables.items():
        for column in df.columns:
            if column in MONETARY_COLUMNS:
                null_count = int(df[column].isna().sum())
                negative_count = int((df[column] < 0).sum()) if pd.api.types.is_numeric_dtype(df[column]) else 0
                rows.append(
                    {
                        "table": table_name,
                        "column": column,
                        "check": "numeric_parse_and_sign",
                        "null_count": null_count,
                        "issue_count": negative_count,
                        "status": "REVIEW" if null_count or negative_count else "PASS",
                    }
                )
            elif column in DATE_COLUMNS:
                null_count = int(df[column].isna().sum())
                rows.append(
                    {
                        "table": table_name,
                        "column": column,
                        "check": "date_parse",
                        "null_count": null_count,
                        "issue_count": null_count,
                        "status": "REVIEW" if null_count else "PASS",
                    }
                )
    return pd.DataFrame(rows)


def validate_business_data_quality(tables: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    interactions = tables["interactions"]
    customers = tables["customers"]
    rows = [
        {
            "check_id": "DQ01",
            "table": "interactions",
            "check": "missing_interaction_end_time",
            "issue_count": int(interactions["interaction_end_time"].astype("string").eq("").sum()),
            "classification": "Data-quality issue",
        },
        {
            "check_id": "DQ02",
            "table": "interactions",
            "check": "missing_agent_notes",
            "issue_count": int(interactions["agent_notes"].astype("string").str.strip().eq("").sum()),
            "classification": "Data-quality issue",
        },
        {
            "check_id": "DQ03",
            "table": "customers",
            "check": "city_not_proper_case",
            "issue_count": int((customers["city"].astype("string") != customers["city"].astype("string").str.title()).sum()),
            "classification": "Data-quality issue",
        },
    ]
    return pd.DataFrame(rows)


def run_data_validation(tables: Dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    return {
        "identifier_preservation": validate_identifier_columns(tables),
        "primary_keys": validate_primary_keys(tables),
        "foreign_keys": validate_foreign_keys(tables),
        "dates_amounts": validate_dates_amounts(tables),
        "business_data_quality": validate_business_data_quality(tables),
    }
