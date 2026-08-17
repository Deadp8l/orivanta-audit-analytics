from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from config import SOURCE_DIR
from data_validation import load_tables, apply_schema, validate_identifier_columns


def test_identifier_columns_are_strings_and_not_nan():
    tables = apply_schema(load_tables(SOURCE_DIR))
    validation = validate_identifier_columns(tables)
    assert (validation['literal_nan_count'] == 0).all()
    assert (validation['status'] == 'PASS').all()
    for frame in tables.values():
        for column in [c for c in frame.columns if c.endswith('_id')]:
            assert str(frame[column].dtype) == 'string'
