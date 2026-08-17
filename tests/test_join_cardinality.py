from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from config import SOURCE_DIR
from data_validation import load_tables, apply_schema


def test_core_dimension_joins_do_not_multiply_transactions():
    tables = apply_schema(load_tables(SOURCE_DIR))
    credits = tables['credits_adjustments']
    joined = credits.merge(tables['accounts'][['account_id','customer_id']], on='account_id', how='left', suffixes=('','_account'))
    assert len(joined) == len(credits)
    joined = credits.merge(tables['agents'][['agent_id','employment_status']], on='agent_id', how='left')
    assert len(joined) == len(credits)
    charges = tables['charges']
    joined = charges.merge(tables['products_services'][['product_service_id','product_category']], on='product_service_id', how='left')
    assert len(joined) == len(charges)
