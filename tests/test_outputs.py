from pathlib import Path
import json
import sys
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from config import OUT_INDEPENDENT, OUT_QA, OUT_VALIDATION, PROJECT_ROOT


def test_required_outputs_integrity_and_exposure_reconciliation():
    required = [
        OUT_INDEPENDENT / 'audit_exceptions.csv',
        OUT_INDEPENDENT / 'test_summary.csv',
        OUT_INDEPENDENT / 'exposure_bridge.csv',
        OUT_INDEPENDENT / 'independent_results_hashes.csv',
        OUT_INDEPENDENT / 'independent_results_freeze_manifest.json',
        OUT_VALIDATION / 'validation_summary.csv',
        OUT_QA / 'execution_manifest.json',
    ]
    assert all(path.exists() and path.stat().st_size > 0 for path in required)
    manifest = json.loads((OUT_QA / 'execution_manifest.json').read_text())
    assert manifest['original_dataset_zip_verified'] is True
    assert manifest['original_source_hashes_unchanged'] is True
    assert manifest['working_source_hashes_unchanged'] is True
    assert manifest['answer_key_hash_unchanged'] is True
    assert manifest['answer_key_accessed_before_freeze'] is False
    bridge = pd.read_csv(OUT_INDEPENDENT / 'exposure_bridge.csv').set_index('exposure_class')['amount']
    assert round(bridge['Gross overlapping flagged amount'] - bridge['Overlap removed'], 2) == round(bridge['Record-level deduplicated flagged amount'], 2)
    assert bridge['Confirmed loss'] == 0
    assert not (PROJECT_ROOT / 'data' / 'synthetic_source' / 'audit_exceptions_answer_key.csv').exists()
