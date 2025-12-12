from __future__ import annotations

from typing import Any, Dict

from app.services.feature_pipeline import get_feature_pipeline


def compute_features(source_type: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Compute core features from normalized payload via FeaturePipeline."""
    pipeline = get_feature_pipeline()
    payload = pipeline.ingest(source_type, params)

    txns = payload.get("transactions", [])
    accounts = payload.get("accounts", [])

    txn_count = len(txns)
    deposits = [t["amount"] for t in txns if t.get("amount", 0) > 0]
    payments = [t["amount"] for t in txns if t.get("amount", 0) < 0]

    avg_deposit = (sum(deposits) / len(deposits)) if deposits else 0.0
    avg_payment = (sum(payments) / len(payments)) if payments else 0.0
    net_flow_30d = sum(t.get("amount", 0) for t in txns)
    balance_total = sum(a.get("balance", 0) for a in accounts)

    return {
        "party_id": payload.get("party", {}).get("party_id"),
        "txn_count": txn_count,
        "avg_deposit": round(avg_deposit, 2),
        "avg_payment": round(avg_payment, 2),
        "net_flow_30d": round(net_flow_30d, 2),
        "balance_total": round(balance_total, 2),
    }
