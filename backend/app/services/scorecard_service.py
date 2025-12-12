from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, NamedTuple, Optional
from sqlalchemy.orm import Session

from app.services.feature_service import compute_features
from app.rules.evaluator import get_evaluator
from app.models.models import ScoreRequest, Feature, AuditLog


class ScoringRule(NamedTuple):
    """Lightweight scoring rule for scorecard evaluation."""
    name: str
    expression: str
    weight: int


# Default scorecard rules
DEFAULT_RULES = [
    ScoringRule(name="positive_net_flow", expression="net_flow_30d > 0", weight=20),
    ScoringRule(name="sufficient_balance", expression="balance_total >= 500", weight=15),
    ScoringRule(name="active_transactions", expression="txn_count >= 2", weight=10),
    ScoringRule(name="healthy_deposits", expression="avg_deposit > 20", weight=25),
    ScoringRule(name="manageable_payments", expression="avg_payment > -100", weight=30),
]


def compute_score(
    source_type: str,
    params: Dict[str, Any],
    rules: List[ScoringRule] | None = None,
    db: Optional[Session] = None,
    persist: bool = True,
) -> Dict[str, Any]:
    """Compute scorecard-based score for a party using feature-driven rules.

    Returns:
        {
            "party_id": str,
            "features": {...},
            "rules": [{"name": str, "passed": bool, "weight": int, ...}],
            "total_score": int (0-100),
            "band": str ("excellent", "good", "fair", "poor"),
        }
    """
    if rules is None:
        rules = DEFAULT_RULES

    # Compute features
    features = compute_features(source_type, params)
    party_id = features["party_id"]

    # Evaluate rules
    evaluator = get_evaluator()
    rule_results = []
    earned_points = 0
    total_possible = sum(r.weight for r in rules)

    for rule in rules:
        try:
            passed = evaluator.evaluate(rule.expression, features)
            error = None
        except Exception as e:
            passed = False
            error = str(e)
        
        if passed:
            earned_points += rule.weight
        
        rule_results.append(
            {
                "name": rule.name,
                "expression": rule.expression,
                "passed": passed,
                "weight": rule.weight,
                "error": error,
            }
        )

    # Normalize to 0-100
    score = int((earned_points / total_possible) * 100) if total_possible > 0 else 0

    # Determine band
    if score >= 80:
        band = "excellent"
    elif score >= 60:
        band = "good"
    elif score >= 40:
        band = "fair"
    else:
        band = "poor"

    result = {
        "party_id": party_id,
        "features": features,
        "rules": rule_results,
        "total_score": score,
        "band": band,
        "computed_at": datetime.utcnow().isoformat() + "Z",
        "source_type": source_type,
    }

    # Persist to database if requested and db session provided
    if persist and db is not None:
        try:
            _persist_score_result(db, party_id, result, source_type)
        except Exception as e:
            # Log error but don't fail the scoring
            print(f"Warning: Failed to persist score: {e}")

    return result


def _persist_score_result(db: Session, party_id: str, result: Dict[str, Any], source_type: str) -> None:
    """Persist score result, features, and audit log to database."""
    
    # 1. Save score request
    score_request = ScoreRequest(
        id=str(uuid.uuid4()),
        party_id=int(party_id.split("-")[1]) if party_id.startswith("P-") else 0,  # Extract numeric ID
        request_timestamp=datetime.utcnow(),
        model_version="scorecard_v2",
        model_type="scorecard",
        final_score=result["total_score"],
        score_band=result["band"],
        decision="APPROVE" if result["total_score"] >= 60 else "REVIEW",
        decision_reasons=json.dumps([r["name"] for r in result["rules"] if r["passed"]]),
        features_snapshot=json.dumps(result["features"]),
        confidence_level=_calculate_confidence(result)
    )
    db.add(score_request)
    
    # 2. Save individual features
    for feature_name, feature_value in result["features"].items():
        if feature_name == "party_id":
            continue
        
        feature = Feature(
            party_id=score_request.party_id,
            feature_name=feature_name,
            feature_value=float(feature_value) if isinstance(feature_value, (int, float)) else 0.0,
            source_type=source_type.upper(),
            computation_timestamp=datetime.utcnow(),
            feature_version="v2"
        )
        db.add(feature)
    
    # 3. Audit log
    audit = AuditLog(
        event_type="COMPUTE_SCORE",
        party_id=score_request.party_id,
        timestamp=datetime.utcnow(),
        request_payload=json.dumps({
            "source": source_type,
            "score": result["total_score"],
            "band": result["band"],
            "rules_passed": sum(1 for r in result["rules"] if r["passed"])
        })
    )
    db.add(audit)
    
    db.commit()


def _calculate_confidence(result: Dict[str, Any]) -> float:
    """Calculate confidence score based on feature availability and rule coverage."""
    features = result.get("features", {})
    rules = result.get("rules", [])
    
    # Base confidence on feature completeness
    feature_count = len([v for k, v in features.items() if k != "party_id" and v is not None])
    feature_confidence = min(feature_count / 5.0, 1.0)  # Assume 5 key features
    
    # Factor in rule evaluation success
    total_rules = len(rules)
    evaluated_rules = sum(1 for r in rules if r.get("error") is None)
    rule_confidence = evaluated_rules / total_rules if total_rules > 0 else 0.5
    
    # Combined confidence
    return round((feature_confidence * 0.6 + rule_confidence * 0.4), 2)
