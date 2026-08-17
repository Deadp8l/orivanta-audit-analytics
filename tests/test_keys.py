from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from config import SOURCE_DIR
from data_validation import load_tables, apply_schema, validate_primary_keys


def test_primary_keys_unique():
    tables = apply_schema(load_tables(SOURCE_DIR))
    result = validate_primary_keys(tables)
    assert (result['blank_keys'] == 0).all()
    assert (result['duplicate_keys'] == 0).all()
    assert (result['status'] == 'PASS').all()
