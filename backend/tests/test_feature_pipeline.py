import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.services.feature_pipeline import get_feature_pipeline


def test_pipeline_ingest_caches_results():
    pipeline = get_feature_pipeline(ttl_seconds=300)
    params = {"party_id": "P-777", "name": "Bob", "accounts": 1, "transactions_per_account": 2}

    first = pipeline.ingest("synthetic", params)
    second = pipeline.ingest("synthetic", params)

    assert first == second
    assert first["party"]["party_id"] == "P-777"
    assert len(first["accounts"]) == 1
    assert len(first["transactions"]) == 2


def test_pipeline_ingest_cache_key_isolated_per_source():
    pipeline = get_feature_pipeline(ttl_seconds=300)
    params = {"party_id": "P-888", "name": "Eve", "accounts": 1, "transactions_per_account": 1}

    payload = pipeline.ingest("synthetic", params)
    assert payload["party"]["party_id"] == "P-888"
