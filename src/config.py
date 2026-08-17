from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = PROJECT_ROOT / "data" / "synthetic_source"
ORIGINAL_SOURCE_DIR = SOURCE_DIR
ANSWER_KEY_PATH = PROJECT_ROOT / "data" / "benchmark" / "audit_exceptions_answer_key.csv"
OUT_INDEPENDENT = PROJECT_ROOT / "results"
OUT_QA = PROJECT_ROOT / "qa"
OUT_VALIDATION = PROJECT_ROOT / "validation"
SQL_DIR = PROJECT_ROOT / "sql"
RUN_DATE = "2026-07-12"
DISCLOSURE = (
    "This project uses a fully synthetic dataset created for audit analytics, data analysis, SQL, "
    "Python, and Power BI portfolio development. All customers, employees, transactions, "
    "conversations, and events are fictional."
)
