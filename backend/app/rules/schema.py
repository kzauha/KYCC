"""Pydantic schemas for rule definitions and evaluation results."""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime


class RuleDefinition(BaseModel):
    """Schema for a decision rule."""
    
    rule_id: str = Field(..., description="Unique rule identifier")
    name: str = Field(..., description="Human-readable rule name")
    expression: str = Field(..., description="Rule condition expression (e.g., 'kyc_score < 50')")
    action: str = Field(..., description="Action if rule matches: 'reject', 'flag', 'approve', 'manual_review'")
    reason: str = Field(..., description="Explanation why this rule exists")
    priority: int = Field(default=100, description="Rule evaluation priority (lower = higher priority)")
    is_active: bool = Field(default=True, description="Whether rule is active")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "rule_id": "rule_001",
                "name": "KYC Threshold Check",
                "expression": "kyc_score < 50",
                "action": "reject",
                "reason": "KYC score below acceptable threshold",
                "priority": 1,
                "is_active": True
            }
        }
    )


class RuleResult(BaseModel):
    """Result of rule evaluation."""
    
    rule_id: str = Field(..., description="Which rule was evaluated")
    matched: bool = Field(..., description="Whether rule condition evaluated to True")
    action: str = Field(..., description="Action to take if matched")
    reason: str = Field(..., description="Rule explanation")
    priority: int = Field(..., description="Rule priority")
    evaluation_error: Optional[str] = Field(default=None, description="Error if evaluation failed")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "rule_id": "rule_001",
                "matched": True,
                "action": "reject",
                "reason": "KYC score below acceptable threshold",
                "priority": 1,
                "evaluation_error": None
            }
        }
    )


class RulesEvaluationResult(BaseModel):
    """Complete result of evaluating all rules for a scoring request."""
    
    party_id: int = Field(..., description="Party being scored")
    triggered_rules: List[RuleResult] = Field(default_factory=list, description="Rules that matched")
    final_decision: str = Field(default="approved", description="Final decision after all rules")
    evaluation_timestamp: datetime = Field(default_factory=datetime.utcnow, description="When evaluation occurred")
    features_snapshot: Dict[str, Any] = Field(default_factory=dict, description="Features used for evaluation")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "party_id": 42,
                "triggered_rules": [
                    {
                        "rule_id": "rule_001",
                        "matched": True,
                        "action": "reject",
                        "reason": "KYC score below threshold",
                        "priority": 1,
                        "evaluation_error": None
                    }
                ],
                "final_decision": "rejected",
                "evaluation_timestamp": "2025-12-12T14:32:10.123456",
                "features_snapshot": {"kyc_score": 30, "transaction_count": 5}
            }
        }
    )
