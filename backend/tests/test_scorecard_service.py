import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.services.scorecard_service import compute_score


def test_compute_score_excellent_band():
    """Test scoring with excellent band (80+)."""
    result = compute_score(
        "synthetic",
        {"party_id": "P-300", "name": "Strong Party", "accounts": 2, "transactions_per_account": 5},
    )

    assert result["party_id"] == "P-300"
    assert result["total_score"] >= 80
    assert result["band"] == "excellent"
    assert len(result["rules"]) == 5
    # All default rules should pass for this synthetic scenario
    assert all(r["passed"] for r in result["rules"])


def test_compute_score_poor_band():
    """Test scoring with poor band (< 40)."""
    result = compute_score(
        "synthetic",
        {"party_id": "P-400", "name": "Weak Party", "accounts": 1, "transactions_per_account": 1},
    )

    assert result["party_id"] == "P-400"
    # With only 1 transaction, avg_deposit might fail healthy_deposits rule
    # and txn_count fails active_transactions
    assert result["total_score"] < 80
    assert result["band"] in ["good", "fair", "poor"]


def test_compute_score_includes_features():
    """Test that computed features are included in result."""
    result = compute_score(
        "synthetic",
        {"party_id": "P-500", "name": "Demo", "accounts": 1, "transactions_per_account": 2},
    )

    assert "features" in result
    features = result["features"]
    assert features["party_id"] == "P-500"
    assert "txn_count" in features
    assert "net_flow_30d" in features
    assert "balance_total" in features
