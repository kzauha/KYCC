# KYC Feature Extractor

The KYC Feature Extractor derives features from party profile data (KYC - Know Your Customer).

## Overview

| Property | Value |
|----------|-------|
| Location | `backend/app/extractors/kyc_extractor.py` |
| Source Type | `KYC` |
| Source Table | `parties` |
| Features | 5 |

---

## Features Extracted

### kyc_verified

Indicates whether the party has passed KYC verification.

| Property | Value |
|----------|-------|
| Type | Binary |
| Range | 0 or 1 |
| Default | 0 |
| Confidence | 1.0 |

**Logic**:
```python
feature_value = float(party.kyc_verified)
```

**Significance**: Verified parties have confirmed identity, reducing fraud risk.

---

### company_age_years

Number of years since the company was created.

| Property | Value |
|----------|-------|
| Type | Numeric |
| Range | 0 to unlimited |
| Default | 0 |
| Confidence | 0.9 |

**Logic**:
```python
years = (reference_date - party.created_at).days / 365.25
feature_value = max(0.0, years)
```

**Significance**: Older companies are generally more stable and lower risk.

---

### party_type_score

Numerical score based on the party's role in the supply chain.

| Property | Value |
|----------|-------|
| Type | Categorical encoded |
| Range | 5 to 10 |
| Default | 5 |
| Confidence | 1.0 |

**Encoding**:

| Party Type | Score |
|------------|-------|
| manufacturer | 10 |
| distributor | 8 |
| supplier | 7 |
| retailer | 6 |
| customer | 5 |

**Logic**:
```python
party_type_scores = {
    "manufacturer": 10,
    "distributor": 8,
    "supplier": 7,
    "retailer": 6,
    "customer": 5
}
party_type_key = party.party_type.lower()
feature_value = party_type_scores.get(party_type_key, 5)
```

**Significance**: Different party types have different risk profiles based on their position in the supply chain.

---

### contact_completeness

Percentage of contact information fields that are filled.

| Property | Value |
|----------|-------|
| Type | Percentage |
| Range | 0 to 100 |
| Default | 0 |
| Confidence | 1.0 |

**Fields Checked**:
- contact_person
- email
- phone
- address

**Logic**:
```python
contact_fields = [party.contact_person, party.email, party.phone, party.address]
completeness = sum(1 for f in contact_fields if f) / len(contact_fields)
feature_value = completeness * 100
```

**Significance**: Complete profiles indicate professional operations and easier communication.

---

### has_tax_id

Indicates whether the party has a tax ID on file.

| Property | Value |
|----------|-------|
| Type | Binary |
| Range | 0 or 1 |
| Default | 0 |
| Confidence | 1.0 |

**Logic**:
```python
feature_value = 1.0 if party.tax_id else 0.0
```

**Significance**: Missing tax IDs are red flags for legitimacy and compliance.

---

## Implementation

```python
class KYCFeatureExtractor(BaseFeatureExtractor):
    """Extract features from Party (KYC) data"""
    
    def get_source_type(self) -> str:
        return "KYC"
    
    def extract(self, party_id: int, db, as_of_date: datetime = None) -> List[FeatureExtractorResult]:
        party = db.query(Party).filter(Party.id == party_id).first()
        
        if not party:
            return []
        
        ref_date = as_of_date or datetime.utcnow()
        features = []
        
        # kyc_verified
        features.append(FeatureExtractorResult(
            feature_name="kyc_verified",
            feature_value=float(party.kyc_verified),
            confidence=1.0
        ))
        
        # company_age_years
        if party.created_at:
            years = (ref_date - party.created_at).days / 365.25
            features.append(FeatureExtractorResult(
                feature_name="company_age_years",
                feature_value=max(0.0, years),
                confidence=0.9
            ))
        
        # party_type_score
        party_type_scores = {
            "manufacturer": 10,
            "distributor": 8,
            "supplier": 7,
            "retailer": 6,
            "customer": 5
        }
        party_type_key = party.party_type.lower() if party.party_type else "customer"
        features.append(FeatureExtractorResult(
            feature_name="party_type_score",
            feature_value=party_type_scores.get(party_type_key, 5),
            confidence=1.0
        ))
        
        # contact_completeness
        contact_fields = [party.contact_person, party.email, party.phone, party.address]
        completeness = sum(1 for f in contact_fields if f) / len(contact_fields)
        features.append(FeatureExtractorResult(
            feature_name="contact_completeness",
            feature_value=completeness * 100,
            confidence=1.0
        ))
        
        # has_tax_id
        features.append(FeatureExtractorResult(
            feature_name="has_tax_id",
            feature_value=1.0 if party.tax_id else 0.0,
            confidence=1.0
        ))
        
        return features
```

---

## Usage

```python
from app.extractors.kyc_extractor import KYCFeatureExtractor

extractor = KYCFeatureExtractor()
features = extractor.extract(party_id=123, db=session)

for f in features:
    print(f"{f.feature_name}: {f.feature_value}")
```

Output:
```
kyc_verified: 1.0
company_age_years: 3.5
party_type_score: 8
contact_completeness: 75.0
has_tax_id: 1.0
```

---

## Temporal Analysis

When `as_of_date` is provided, the extractor calculates age relative to that date:

```python
# Age as of January 1, 2024
features = extractor.extract(
    party_id=123, 
    db=session, 
    as_of_date=datetime(2024, 1, 1)
)
```

This enables historical analysis and prevents data leakage in training.
