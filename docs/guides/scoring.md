# Credit Scoring Guide

## Overview

KYCC implements a transparent, explainable credit scoring system using a weighted scorecard model. This guide explains how scores are computed, what factors matter, and how to interpret results.

## Scoring Pipeline

The scoring process follows five stages:

```
1. Feature Extraction → 2. Normalization → 3. Scorecard Application →
4. Decision Rules → 5. Audit Logging
```

---

## Stage 1: Feature Extraction

Features are extracted from three independent sources in parallel.

### KYC Features (4 features)

Extracted from the `parties` table:

| Feature | Description | Range | Weight |
|---------|-------------|-------|--------|
| `kyc_score` | KYC verification score | 0-100 | 0.20 |
| `company_age_days` | Days since company created | 0-∞ | 0.10 |
| `party_type_encoded` | Numeric encoding of party type | 1-5 | 0.05 |
| `contact_completeness` | % of contact fields filled | 0-100 | 0.00 |

**Why these matter**:
- **kyc_score**: Higher compliance = lower regulatory risk
- **company_age_days**: Older companies = more established
- **party_type**: Some types inherently lower risk (e.g., manufacturers)
- **contact_completeness**: Better data quality = more reliable

### Transaction Features (4 features)

Extracted from the `transactions` table:

| Feature | Description | Calculation | Weight |
|---------|-------------|-------------|--------|
| `transaction_count` | Total transactions | COUNT(*) | 0.25 |
| `avg_transaction_amount` | Mean transaction value | AVG(amount) | 0.05 |
| `transaction_regularity` | Consistency of txns | 1 - (stddev / mean) | 0.15 |
| `days_since_last_transaction` | Recency | NOW() - MAX(date) | 0.10 |

**Why these matter**:
- **transaction_count**: More history = better assessment
- **avg_amount**: Transaction size indicates business scale
- **regularity**: Consistent activity = stable business
- **recency**: Recent activity = currently operating

### Network Features (3 features)

Extracted from the `relationships` table via graph traversal:

| Feature | Description | Calculation | Weight |
|---------|-------------|-------------|--------|
| `network_size` | Parties in component | BFS/DFS count | 0.10 |
| `counterparty_count` | Direct neighbors | COUNT(suppliers + customers) | 0.05 |
| `network_depth` | Max relationship hops | Longest path length | 0.00 |

**Why these matter**:
- **network_size**: Larger network = more integrated
- **counterparty_count**: Diversified relationships = lower concentration risk
- **network_depth**: Deep integration = important supply chain player

---

## Stage 2: Normalization

Raw features are scaled to 0-1 range using **min-max normalization**:

```
normalized = (value - min) / (max - min)
```

### Example Normalization

```python
# Raw values
kyc_score = 85          # Range: 0-100
company_age_days = 180  # Range: 0-365 (assume max 1 year)
transaction_count = 15  # Range: 0-20 (assume max for normalization)

# Normalized values
kyc_norm = 85 / 100 = 0.85
age_norm = 180 / 365 = 0.49
count_norm = 15 / 20 = 0.75
```

**Why normalize?**
- Features have different units (days, dollars, counts)
- Weights apply consistently across all features
- Prevents large-value features from dominating

---

## Stage 3: Scorecard Application

The scorecard formula:

```
raw_score = intercept + Σ(normalized_feature[i] × weight[i])
```

### Default Scorecard Weights

| Feature Category | Weight Sum | % of Total Score |
|------------------|------------|------------------|
| Transaction Features | 0.55 | 55% |
| KYC Features | 0.35 | 35% |
| Network Features | 0.15 | 15% |

### Step-by-Step Calculation

```python
# Step 1: Apply weights
contributions = {
    'kyc_score': 0.85 × 0.20 = 0.170,
    'company_age_days': 0.49 × 0.10 = 0.049,
    'party_type_encoded': 0.20 × 0.05 = 0.010,
    'transaction_count': 0.75 × 0.25 = 0.1875,
    'avg_transaction_amount': 0.67 × 0.05 = 0.0335,
    'transaction_regularity': 0.96 × 0.15 = 0.144,
    'days_since_last_transaction': 0.99 × 0.10 = 0.099,
    'network_size': 0.33 × 0.10 = 0.033,
    'counterparty_count': 0.25 × 0.05 = 0.0125,
}

# Step 2: Sum contributions
raw_score = 0.0 + sum(contributions.values()) = 0.769

# Step 3: Scale to 300-900 range
final_score = 300 + (raw_score × 600) = 300 + 461.4 = 761
```

### Score Bands

| Band | Range | Risk Level | Typical Action |
|------|-------|------------|----------------|
| **Excellent** | 800-900 | Very Low | Auto-approve, best rates |
| **Good** | 650-799 | Low | Approve, standard rates |
| **Fair** | 550-649 | Medium | Manual review required |
| **Poor** | 300-549 | High | Reject or require collateral |

---

## Stage 4: Decision Rules

After computing the score, business rules are evaluated in **priority order** (first match wins).

### Example Rules

| Priority | Condition | Action | Reason |
|----------|-----------|--------|--------|
| 1 | `transaction_count == 0` | REJECT | No transaction history |
| 2 | `kyc_score < 40` | REJECT | Poor KYC compliance |
| 3 | `network_size < 2` | FLAG | Isolated in supply chain |
| 4 | `company_age_days < 30` | MANUAL_REVIEW | Too new to assess |
| 5 | `final_score > 800` | APPROVE | Excellent score |
| 6 | `final_score > 650` | APPROVE | Good score |
| 7 | `final_score > 550` | MANUAL_REVIEW | Fair score |
| 8 | `final_score <= 550` | REJECT | Poor score |

### Rule Evaluation Example

```python
# Party: ACME Suppliers, Score: 761
# Rules evaluated in priority order:

Rule 1: transaction_count == 0? NO (count=15) → Skip
Rule 2: kyc_score < 40? NO (score=85) → Skip
Rule 3: network_size < 2? NO (size=2) → Skip
Rule 4: company_age_days < 30? NO (age=180) → Skip
Rule 5: final_score > 800? NO (score=761) → Skip
Rule 6: final_score > 650? YES ✓ → MATCH!

Decision: APPROVE
Reason: "Rule 6: Approve if final_score > 650"
```

---

## Stage 5: Audit Logging

Every score computation creates a `score_requests` record containing:

- Complete feature snapshot (JSON)
- Model version used
- Raw and final scores
- Decision and reasons
- Processing time
- Timestamp

**Benefits**:
- **Explainability**: Show which features drove the score
- **Reproducibility**: Replay old scores with old features
- **Debugging**: Investigate unexpected scores
- **Compliance**: Full audit trail for regulators

---

## Confidence Score

Confidence indicates data completeness:

```
confidence = available_features / total_expected_features
```

### Confidence Levels

| Confidence | Interpretation | Recommended Action |
|------------|----------------|-------------------|
| 1.0 | All features available | Fully trust score |
| 0.8-0.99 | Most features available | Trust score, note missing data |
| 0.5-0.79 | Partial feature set | Use cautiously, flag for review |
| < 0.5 | Insufficient data | Do not use score, collect more data |

---

## Feature Importance

Features ranked by weight (importance):

1. **transaction_count** (0.25) - Most important
2. **kyc_score** (0.20)
3. **transaction_regularity** (0.15)
4. **company_age_days** (0.10)
5. **days_since_last_transaction** (0.10)
6. **network_size** (0.10)
7. **avg_transaction_amount** (0.05)
8. **counterparty_count** (0.05)
9. **party_type_encoded** (0.05)

Weights sum to **1.0** (100% of score).

---

## Score Interpretation

### Example: ACME Suppliers (Score: 761)

**Score Breakdown**:
```
Raw Score: 0.769 (76.9% of max)
Final Score: 761 (300-900 scale)
Band: GOOD
Decision: APPROVE
Confidence: 0.91 (91% data completeness)
```

**Top Positive Factors**:
1. `transaction_count`: 15 txns (contributed 0.1875 = 18.75% of score)
2. `kyc_score`: 85/100 (contributed 0.170 = 17.0%)
3. `transaction_regularity`: 0.96 (contributed 0.144 = 14.4%)

**Interpretation**: ACME has consistent transaction history, good KYC compliance, and regular business activity → Low risk, approved.

### Example: Local Retailer (Score: 425)

**Score Breakdown**:
```
Raw Score: 0.208 (20.8% of max)
Final Score: 425
Band: POOR
Decision: REJECT
Confidence: 0.73 (73% data completeness)
```

**Negative Factors**:
1. `transaction_count`: Only 2 txns (low history)
2. `company_age_days`: 30 days (very new company)
3. `network_size`: 1 (isolated, no diversification)

**Interpretation**: Insufficient transaction history, new company, isolated in supply chain → High risk, rejected.

---

## Model Versioning

Scoring models are versioned in `model_registry`:

```sql
SELECT model_version, deployed_date, is_active
FROM model_registry
ORDER BY deployed_date DESC;

-- Result:
-- default_scorecard_v1  2025-12-01  1 (active)
-- experimental_ml_v1    2025-11-15  0 (inactive)
```

**Benefits of Versioning**:
- A/B test new models
- Rollback to previous version if needed
- Compare model performance over time

---

## Customizing Scoring

### Adjust Weights

To increase emphasis on KYC:

```python
weights = {
    'kyc_score': 0.30,  # Increased from 0.20
    'transaction_count': 0.20,  # Decreased from 0.25
    # ... other weights adjusted to sum to 1.0
}
```

### Add Custom Features

1. Create new extractor inheriting `BaseFeatureExtractor`
2. Implement `extract()` method
3. Register in `FeaturePipelineService`
4. Add weight to scorecard model
5. Update `feature_definitions` table

### Change Decision Rules

```sql
-- Disable rule
UPDATE decision_rules SET is_active = 0 WHERE rule_id = 'RULE_003';

-- Add new rule
INSERT INTO decision_rules (rule_id, rule_name, condition_expression, action, priority, is_active)
VALUES ('RULE_010', 'Flag high-value new companies', 'avg_transaction_amount > 10000 AND company_age_days < 90', 'FLAG', 10, 1);
```

---

## Best Practices

### For Accurate Scoring
1. **Keep data current**: Refresh features every 7 days
2. **Validate inputs**: Ensure transaction data is clean
3. **Monitor confidence**: Investigate low-confidence scores
4. **Review outliers**: Manually check extreme scores (< 400 or > 850)

### For Fairness
1. **Avoid bias**: Ensure features don't proxy for protected classes
2. **Transparent weights**: Document why features are weighted
3. **Regular audits**: Review decision patterns for disparate impact
4. **Explainability**: Always provide score breakdown

### For Performance
1. **Cache features**: Use TTL cache (already implemented)
2. **Batch scoring**: Score multiple parties in one transaction
3. **Async processing**: For batch jobs, use background tasks
4. **Index optimization**: Ensure `party_id`, `feature_name` indexed

---

## Troubleshooting

### Score Seems Too Low

1. Check feature values: `GET /api/scoring/features/{party_id}`
2. Verify transaction count > 0
3. Check KYC score (should be ≥ 40)
4. Ensure network connections exist

### Score Not Updating

1. Clear feature cache: `POST /api/scoring/compute-features/{party_id}`
2. Check `valid_to` is NULL for current features
3. Verify new transactions are in database

### Decision Doesn't Match Score

1. Check decision rules: `SELECT * FROM decision_rules WHERE is_active = 1`
2. Review rule priorities (lower = evaluated first)
3. Verify rule conditions match feature values

---

## Further Reading

- [API Reference: Scoring](../api/scoring.md)
- [Database Schema: Features](../database/schema.md#features)
- [Architecture: Service Layer](../architecture.md#service-layer)
