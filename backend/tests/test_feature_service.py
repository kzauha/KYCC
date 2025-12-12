import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.services.feature_service import compute_features


def test_compute_features_basic():
    features = compute_features(
        "synthetic",
        {"party_id": "P-200", "name": "Demo", "accounts": 1, "transactions_per_account": 2},
    )

    assert features["party_id"] == "P-200"
    assert features["txn_count"] == 2
    # deposits: [27.5], payments: [-20]
    assert features["avg_deposit"] == 27.5
    assert features["avg_payment"] == -20.0
    assert features["net_flow_30d"] == 7.5
    assert features["balance_total"] == 1000.0
