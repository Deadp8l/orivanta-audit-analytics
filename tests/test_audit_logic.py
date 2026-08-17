from pathlib import Path
import re
import sys
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from config import SOURCE_DIR, PROJECT_ROOT, OUT_INDEPENDENT
from data_validation import load_tables, apply_schema
from audit_functions import run_all_tests


def test_all_40_tests_execute_without_benchmark_caps_and_sql_reconciles():
    tables = apply_schema(load_tables(SOURCE_DIR))
    exceptions, summary = run_all_tests(tables)
    assert list(summary['test_id']) == [f'T{i:02d}' for i in range(1, 41)]
    assert len(exceptions) == int(summary['rows'].sum())
    source = (PROJECT_ROOT / 'src' / 'audit_functions.py').read_text(encoding='utf-8')
    assert not re.search(r'\.head\s*\(|\.iloc\s*\[\s*:|expected_count|target_count|benchmark_count', source, re.I)
    reconciliation = pd.read_csv(OUT_INDEPENDENT / 'sql_python_reconciliation.csv')
    supported = reconciliation[reconciliation['sql_supported'] == 'Yes']
    assert len(supported) == 37
    assert (supported['status'] == 'PASS').all()
    t39 = summary.loc[summary['test_id'] == 'T39'].iloc[0]
    assert int(t39['rows']) == 20
    assert round(float(t39['direct_measurable_amount']), 2) == 1575.00
