# Decision Rules

Decision rules provide business logic overrides and adjustments to computed scores.

## Overview

| Property | Value |
|----------|-------|
| Location | `backend/app/rules/evaluator.py` |
| Expression Engine | simpleeval |
| Rule Types | override, adjust, flag |

---

## Rule System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                     Rule Evaluation                                 │
│                                                                     │
│   Input: Features + Base Score                                      │
│          │                                                          │
│          ▼                                                          │
│   ┌─────────────────────────────────────────────────────────────┐  │
│   │  Rule 1: KYC Override                                       │  │
│   │  IF kyc_verified == 0 AND company_age_years < 1             │  │
│   │  THEN set_max_score(500)                                    │  │
│   └─────────────────────────────────────────────────────────────┘  │
│          │                                                          │
│          ▼                                                          │
│   ┌─────────────────────────────────────────────────────────────┐  │
│   │  Rule 2: Activity Penalty                                   │  │
│   │  IF recent_activity_flag == 0                               │  │
│   │  THEN adjust_score(-50)                                     │  │
│   └─────────────────────────────────────────────────────────────┘  │
│          │                                                          │
│          ▼                                                          │
│   ┌─────────────────────────────────────────────────────────────┐  │
│   │  Rule 3: Manual Review Flag                                 │  │
│   │  IF network_size == 0                                       │  │
│   │  THEN flag_for_review("no_network")                         │  │
│   └─────────────────────────────────────────────────────────────┘  │
│          │                                                          │
│          ▼                                                          │
│   Output: Adjusted Score + Flags + Applied Rules                    │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Rule Definition

### Structure

```python
RULE = {
    "id": "rule_001",
    "name": "KYC Override",
    "description": "Cap score for unverified new companies",
    "condition": "kyc_verified == 0 and company_age_years < 1",
    "action": {
        "type": "set_max_score",
        "value": 500
    },
    "priority": 1,
    "enabled": True
}
```

### Properties

| Property | Type | Description |
|----------|------|-------------|
| id | string | Unique rule identifier |
| name | string | Human-readable name |
| description | string | Rule explanation |
| condition | string | Expression evaluated by simpleeval |
| action | object | Action to take when condition is true |
| priority | int | Order of evaluation (lower = first) |
| enabled | bool | Whether rule is active |

---

## Action Types

### set_max_score

Caps the score at a maximum value:

```python
{
    "type": "set_max_score",
    "value": 500
}
```

Result: `final_score = min(base_score, 500)`

### set_min_score

Sets a minimum score floor:

```python
{
    "type": "set_min_score",
    "value": 400
}
```

Result: `final_score = max(base_score, 400)`

### adjust_score

Adds or subtracts from the score:

```python
{
    "type": "adjust_score",
    "value": -50
}
```

Result: `final_score = base_score - 50`

### multiply_score

Multiplies the score by a factor:

```python
{
    "type": "multiply_score",
    "value": 0.9
}
```

Result: `final_score = base_score * 0.9`

### flag_for_review

Adds a review flag without changing score:

```python
{
    "type": "flag_for_review",
    "value": "manual_review_required"
}
```

Result: Adds flag to output, score unchanged

---

## Rule Evaluator Implementation

```python
from simpleeval import simple_eval

class RuleEvaluator:
    """Evaluate business rules against features and scores."""
    
    def __init__(self):
        self.rules = self._load_rules()
    
    def evaluate_rules(
        self, 
        features: dict, 
        base_score: int
    ) -> dict:
        """
        Evaluate all rules and return adjustments.
        
        Args:
            features: Feature dictionary
            base_score: Score before rules
            
        Returns:
            dict with final_score, rules_applied, flags
        """
        final_score = base_score
        rules_applied = []
        flags = []
        
        # Sort by priority
        sorted_rules = sorted(
            [r for r in self.rules if r['enabled']],
            key=lambda x: x['priority']
        )
        
        for rule in sorted_rules:
            try:
                # Evaluate condition
                result = simple_eval(
                    rule['condition'],
                    names=features
                )
                
                if result:
                    # Apply action
                    final_score, flag = self._apply_action(
                        rule['action'],
                        final_score
                    )
                    
                    rules_applied.append(rule['id'])
                    if flag:
                        flags.append(flag)
                        
            except Exception as e:
                print(f"Rule {rule['id']} error: {e}")
        
        # Ensure score stays in valid range
        final_score = min(900, max(300, final_score))
        
        return {
            'final_score': final_score,
            'rules_applied': rules_applied,
            'flags': flags,
            'adjustment': final_score - base_score
        }
    
    def _apply_action(self, action: dict, score: int) -> tuple:
        """Apply rule action and return new score and optional flag."""
        action_type = action['type']
        value = action['value']
        
        if action_type == 'set_max_score':
            return min(score, value), None
        elif action_type == 'set_min_score':
            return max(score, value), None
        elif action_type == 'adjust_score':
            return score + value, None
        elif action_type == 'multiply_score':
            return int(score * value), None
        elif action_type == 'flag_for_review':
            return score, value
        else:
            return score, None
```

---

## Default Rules

### Rule: KYC Override

Unverified new companies are capped:

```python
{
    "id": "kyc_override",
    "name": "KYC Override",
    "condition": "kyc_verified == 0 and company_age_years < 1",
    "action": {"type": "set_max_score", "value": 500},
    "priority": 1
}
```

### Rule: No Activity Penalty

No recent activity reduces score:

```python
{
    "id": "no_activity_penalty",
    "name": "No Activity Penalty",
    "condition": "recent_activity_flag == 0",
    "action": {"type": "adjust_score", "value": -30},
    "priority": 2
}
```

### Rule: High Volume Bonus

High transaction volume gets bonus:

```python
{
    "id": "high_volume_bonus",
    "name": "High Volume Bonus",
    "condition": "total_transaction_volume_6m > 500000",
    "action": {"type": "adjust_score", "value": 25},
    "priority": 3
}
```

### Rule: Network Isolation Flag

Isolated parties need review:

```python
{
    "id": "network_isolation_flag",
    "name": "Network Isolation Flag",
    "condition": "network_size == 0 or direct_counterparty_count == 0",
    "action": {"type": "flag_for_review", "value": "isolated_network"},
    "priority": 4
}
```

### Rule: Missing Contact Flag

Incomplete profiles need review:

```python
{
    "id": "missing_contact_flag",
    "name": "Missing Contact Flag",
    "condition": "contact_completeness < 50",
    "action": {"type": "flag_for_review", "value": "incomplete_profile"},
    "priority": 5
}
```

---

## Condition Expressions

### Supported Operators

| Operator | Description | Example |
|----------|-------------|---------|
| == | Equals | `kyc_verified == 1` |
| != | Not equals | `party_type != 'customer'` |
| > | Greater than | `company_age_years > 5` |
| >= | Greater or equal | `transaction_count_6m >= 10` |
| < | Less than | `score < 500` |
| <= | Less or equal | `network_size <= 2` |
| and | Logical AND | `kyc_verified == 1 and company_age_years > 2` |
| or | Logical OR | `kyc_verified == 0 or has_tax_id == 0` |
| not | Logical NOT | `not recent_activity_flag` |

### Available Variables

All features are available as variables:

- `kyc_verified`
- `company_age_years`
- `party_type_score`
- `contact_completeness`
- `has_tax_id`
- `transaction_count_6m`
- `avg_transaction_amount`
- `total_transaction_volume_6m`
- `transaction_regularity_score`
- `recent_activity_flag`
- `direct_counterparty_count`
- `network_depth_downstream`
- `network_size`
- `supplier_count`
- `customer_count`
- `network_balance_ratio`

---

## Usage

### Basic Evaluation

```python
from app.rules.evaluator import evaluate_rules

features = {
    "kyc_verified": 0,
    "company_age_years": 0.5,
    "recent_activity_flag": 1,
    "network_size": 5
}

result = evaluate_rules(features, base_score=650)

print(f"Final Score: {result['final_score']}")
print(f"Rules Applied: {result['rules_applied']}")
print(f"Flags: {result['flags']}")
```

Output:
```
Final Score: 500
Rules Applied: ['kyc_override']
Flags: []
```

### With Integration

```python
# In ScoringService.compute_score()
score_result = compute_scorecard_score(features)
rules_result = evaluate_rules(features, score_result['total_score'])

final_score = rules_result['final_score']
```

---

## Rule Management

### Adding Rules

```python
evaluator = RuleEvaluator()

new_rule = {
    "id": "custom_rule",
    "name": "Custom Rule",
    "condition": "some_feature > threshold",
    "action": {"type": "adjust_score", "value": 10},
    "priority": 10,
    "enabled": True
}

evaluator.add_rule(new_rule)
```

### Disabling Rules

```python
evaluator.disable_rule("kyc_override")
```

### Loading from Database

```python
def _load_rules(self) -> list:
    """Load rules from database or config file."""
    # From database
    db_rules = self.db.query(DecisionRule).filter(
        DecisionRule.enabled == True
    ).all()
    
    return [rule.to_dict() for rule in db_rules]
```

---

## Testing Rules

```python
def test_kyc_override_rule():
    """Test that unverified new companies are capped."""
    features = {
        "kyc_verified": 0,
        "company_age_years": 0.5
    }
    
    result = evaluate_rules(features, base_score=700)
    
    assert result['final_score'] == 500
    assert 'kyc_override' in result['rules_applied']
```
