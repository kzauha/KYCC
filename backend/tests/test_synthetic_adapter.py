import sys
from pathlib import Path

# Ensure backend root is on path when running tests directly
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.adapters.synthetic_adapter import SyntheticAdapter
from app.adapters.registry import get_adapter_registry


def test_synthetic_adapter_parse_basic():
    adapter = SyntheticAdapter()
    payload = adapter.parse({"party_id": "P-123", "name": "Alice"})

    assert payload["party"]["party_id"] == "P-123"
    assert payload["party"]["name"] == "Alice"
    assert len(payload["accounts"]) == 2
    assert len(payload["transactions"]) == 2 * 5
    assert len(payload["relationships"]) == len(payload["accounts"])  # owns links

    # Check deterministic keys
    acc_ids = [a["account_id"] for a in payload["accounts"]]
    assert acc_ids[0].startswith("A-P-123-001")


def test_synthetic_adapter_registry_discovery():
    registry = get_adapter_registry()
    adapter = registry.get("synthetic")
    assert isinstance(adapter, SyntheticAdapter)
