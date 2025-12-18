# Transaction Feature Extractor

The Transaction Feature Extractor derives features from financial transaction history.

## Overview

| Property | Value |
|----------|-------|
| Location | `backend/app/extractors/transaction_extractor.py` |
| Source Type | `TRANSACTIONS` |
| Source Table | `transactions` |
| Features | 5 |
| Time Window | 6 months |

---

## Features Extracted

### transaction_count_6m

Number of transactions in the last 6 months.

| Property | Value |
|----------|-------|
| Type | Count |
| Range | 0 to unlimited |
| Default | 0 |
| Confidence | 1.0 |

**Logic**:
```python
transactions = db.query(Transaction).filter(
    Transaction.party_id == party_id,
    Transaction.transaction_date >= six_months_ago,
    Transaction.transaction_date <= reference_date
).all()

feature_value = float(len(transactions))
```

**Significance**: Active parties with more transactions show healthy business operations.

---

### avg_transaction_amount

Average transaction amount over the period.

| Property | Value |
|----------|-------|
| Type | Currency |
| Range | 0 to unlimited |
| Default | 0 |
| Confidence | 1.0 |

**Logic**:
```python
amounts = [t.amount for t in transactions]
feature_value = sum(amounts) / len(amounts) if amounts else 0
```

**Significance**: Indicates typical deal size and business scale.

---

### total_transaction_volume_6m

Total monetary volume of all transactions.

| Property | Value |
|----------|-------|
| Type | Currency |
| Range | 0 to unlimited |
| Default | 0 |
| Confidence | 1.0 |

**Logic**:
```python
feature_value = sum(t.amount for t in transactions)
```

**Significance**: Higher volume indicates larger business scale and capacity.

---

### transaction_regularity_score

Measures consistency of monthly transaction volumes using coefficient of variation.

| Property | Value |
|----------|-------|
| Type | Percentage |
| Range | 0 to 100 |
| Default | 0 |
| Confidence | 0.9 |

**Logic**:
```python
# Group transactions by month
monthly_volumes = {}
for txn in transactions:
    month_key = txn.transaction_date.strftime("%Y-%m")
    monthly_volumes[month_key] = monthly_volumes.get(month_key, 0.0) + txn.amount

# Calculate coefficient of variation
volumes = list(monthly_volumes.values())
mean_vol = np.mean(volumes)
std_vol = np.std(volumes)

# CV = std / mean (lower is more regular)
cv = std_vol / mean_vol if mean_vol > 0 else 1.0

# Convert to 0-100 score (higher is more regular)
feature_value = max(0, 100 - (cv * 100))
```

**Significance**: Regular, predictable cash flows indicate stable operations.

---

### recent_activity_flag

Binary flag indicating activity in the last 30 days.

| Property | Value |
|----------|-------|
| Type | Binary |
| Range | 0 or 1 |
| Default | 0 |
| Confidence | 1.0 |

**Logic**:
```python
thirty_days_ago = reference_date - timedelta(days=30)
recent_txns = [t for t in transactions if t.transaction_date >= thirty_days_ago]
feature_value = 1.0 if recent_txns else 0.0
```

**Significance**: Recent activity confirms the business is currently operational.

---

## Implementation

```python
class TransactionFeatureExtractor(BaseFeatureExtractor):
    """Extract features from Transaction history"""
    
    def get_source_type(self) -> str:
        return "TRANSACTIONS"
    
    def extract(self, party_id: int, db, as_of_date: datetime = None) -> List[FeatureExtractorResult]:
        features = []
        ref_date = as_of_date or datetime.utcnow()
        six_months_ago = ref_date - timedelta(days=180)
        
        # Query transactions within time window
        transactions = db.query(Transaction).filter(
            Transaction.party_id == party_id,
            Transaction.transaction_date >= six_months_ago,
            Transaction.transaction_date <= ref_date
        ).all()
        
        if not transactions:
            return self._get_default_features()
        
        # transaction_count_6m
        features.append(FeatureExtractorResult(
            feature_name="transaction_count_6m",
            feature_value=float(len(transactions)),
            confidence=1.0
        ))
        
        # avg_transaction_amount
        amounts = [t.amount for t in transactions]
        features.append(FeatureExtractorResult(
            feature_name="avg_transaction_amount",
            feature_value=sum(amounts) / len(amounts),
            confidence=1.0
        ))
        
        # total_transaction_volume_6m
        features.append(FeatureExtractorResult(
            feature_name="total_transaction_volume_6m",
            feature_value=sum(amounts),
            confidence=1.0
        ))
        
        # transaction_regularity_score
        monthly_volumes = {}
        for txn in transactions:
            month_key = txn.transaction_date.strftime("%Y-%m")
            monthly_volumes[month_key] = monthly_volumes.get(month_key, 0.0) + txn.amount
        
        if len(monthly_volumes) >= 2:
            volumes = list(monthly_volumes.values())
            mean_vol = np.mean(volumes)
            std_vol = np.std(volumes)
            cv = std_vol / mean_vol if mean_vol > 0 else 1.0
            regularity = max(0, 100 - (cv * 100))
        else:
            regularity = 50.0  # Default for single month
        
        features.append(FeatureExtractorResult(
            feature_name="transaction_regularity_score",
            feature_value=regularity,
            confidence=0.9
        ))
        
        # recent_activity_flag
        thirty_days_ago = ref_date - timedelta(days=30)
        recent = any(t.transaction_date >= thirty_days_ago for t in transactions)
        features.append(FeatureExtractorResult(
            feature_name="recent_activity_flag",
            feature_value=1.0 if recent else 0.0,
            confidence=1.0
        ))
        
        return features
    
    def _get_default_features(self) -> List[FeatureExtractorResult]:
        """Return default values when no transactions exist."""
        return [
            FeatureExtractorResult("transaction_count_6m", 0.0, 1.0),
            FeatureExtractorResult("avg_transaction_amount", 0.0, 1.0),
            FeatureExtractorResult("total_transaction_volume_6m", 0.0, 1.0),
            FeatureExtractorResult("transaction_regularity_score", 0.0, 0.5),
            FeatureExtractorResult("recent_activity_flag", 0.0, 1.0),
        ]
```

---

## Usage

```python
from app.extractors.transaction_extractor import TransactionFeatureExtractor

extractor = TransactionFeatureExtractor()
features = extractor.extract(party_id=123, db=session)

for f in features:
    print(f"{f.feature_name}: {f.feature_value}")
```

Output:
```
transaction_count_6m: 45.0
avg_transaction_amount: 5250.50
total_transaction_volume_6m: 236272.50
transaction_regularity_score: 78.5
recent_activity_flag: 1.0
```

---

## Temporal Analysis

The extractor respects `as_of_date` for historical analysis:

```python
# Get transaction features as of 6 months ago
features = extractor.extract(
    party_id=123,
    db=session,
    as_of_date=datetime(2024, 1, 1)
)
```

Only transactions with `transaction_date <= as_of_date` are included.

---

## Edge Cases

| Scenario | Behavior |
|----------|----------|
| No transactions | Return default features with 0 values |
| Single transaction | Regularity score = 50 (unknown) |
| All transactions in one month | Regularity score = 50 |
| Negative amounts | Included in calculations (credit notes) |
