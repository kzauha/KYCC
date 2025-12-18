# Score Computation

The scoring system transforms features into credit scores through a multi-stage process.

## Overview

```
Features → Scorecard Engine → Decision Rules → Score Band → Final Result
```

---

## Computation Stages

### Stage 1: Feature Collection

Features are collected from the feature pipeline:

```python
from app.services.feature_pipeline_service import FeaturePipelineService

pipeline = FeaturePipelineService(db)
feature_result = pipeline.extract_all_features(party_id)

# Convert to dictionary
features = {
    f['feature_name']: f['feature_value'] 
    for f in feature_result['features_list']
}
```

### Stage 2: Scorecard Calculation

The scorecard engine computes the raw score:

```python
from app.scorecard.scorecard_engine import compute_scorecard_score

score_result = compute_scorecard_score(features)
# Returns: {total_score, band, components, raw_score, max_possible, version}
```

### Stage 3: Decision Rules

Business rules can override or adjust scores:

```python
from app.rules.evaluator import evaluate_rules

rules_result = evaluate_rules(features, score_result['total_score'])
# Returns: {adjustments, flags, final_score}
```

### Stage 4: Band Assignment

Final score is mapped to a risk band:

```python
from app.scorecard.scorecard_engine import get_score_band

band = get_score_band(final_score)
# Returns: 'excellent', 'good', 'fair', 'poor', or 'very_poor'
```

---

## ScoringService Implementation

### Location
`backend/app/services/scoring_service.py`

### Full Score Computation

```python
class ScoringService:
    def __init__(self, db: Session):
        self.db = db
        self.feature_pipeline = FeaturePipelineService(db)
    
    def compute_score(
        self,
        party_id: int,
        source: str = "database",
        profile_data: dict = None,
        scorecard_version: str = "v1"
    ) -> dict:
        """
        Compute credit score for a party.
        
        Args:
            party_id: ID of the party
            source: 'database' or 'synthetic'
            profile_data: Optional synthetic profile data
            scorecard_version: Scorecard version to use
            
        Returns:
            Complete scoring result
        """
        # Step 1: Get features
        if source == "synthetic" and profile_data:
            features = self._extract_synthetic_features(profile_data)
        else:
            feature_result = self.feature_pipeline.extract_all_features(party_id)
            features = self._flatten_features(feature_result)
        
        # Step 2: Load scorecard config
        scorecard_config = self._get_scorecard_config(scorecard_version)
        
        # Step 3: Compute score
        score_result = compute_scorecard_score(features, scorecard_config)
        
        # Step 4: Apply decision rules
        rules_result = evaluate_rules(features, score_result['total_score'])
        
        # Step 5: Determine final score and band
        final_score = rules_result.get('final_score', score_result['total_score'])
        band = get_score_band(final_score)
        
        # Step 6: Build response
        result = {
            'party_id': party_id,
            'total_score': final_score,
            'band': band,
            'scorecard_version': scorecard_version,
            'components': score_result['components'],
            'rules_applied': rules_result.get('rules_applied', []),
            'explanation': self._generate_explanation(score_result, rules_result),
            'computed_at': datetime.utcnow().isoformat()
        }
        
        # Step 7: Log to database
        self._log_score_request(party_id, result)
        
        return result
```

---

## Feature Flattening

Features from the pipeline are flattened for scorecard input:

```python
def _flatten_features(self, feature_result: dict) -> dict:
    """Convert feature list to dictionary."""
    return {
        f['feature_name']: f['feature_value']
        for f in feature_result['features_list']
    }
```

---

## Synthetic Scoring

For synthetic profiles (without database records):

```python
def _extract_synthetic_features(self, profile_data: dict) -> dict:
    """Extract features from synthetic profile data."""
    from app.adapters.synthetic_adapter import SyntheticAdapter
    
    adapter = SyntheticAdapter()
    normalized = adapter.parse(profile_data)
    
    return {
        'kyc_verified': 1.0 if normalized.get('kyc_verified') else 0.0,
        'company_age_years': normalized.get('company_age_years', 0),
        'party_type_score': self._encode_party_type(normalized.get('party_type')),
        'contact_completeness': normalized.get('contact_completeness', 0),
        'has_tax_id': 1.0 if normalized.get('tax_id') else 0.0,
        'transaction_count_6m': normalized.get('transaction_count', 0),
        'avg_transaction_amount': normalized.get('avg_transaction_amount', 0),
        'total_transaction_volume_6m': normalized.get('total_volume', 0),
        'transaction_regularity_score': normalized.get('regularity_score', 50),
        'recent_activity_flag': 1.0 if normalized.get('recent_activity') else 0.0,
        'direct_counterparty_count': normalized.get('counterparty_count', 0),
        'network_size': normalized.get('network_size', 0),
        'supplier_count': normalized.get('supplier_count', 0),
        'customer_count': normalized.get('customer_count', 0),
        'network_balance_ratio': normalized.get('network_balance', 0.5)
    }
```

---

## Score Logging

Every score computation is logged:

```python
def _log_score_request(self, party_id: int, result: dict):
    """Log score request to database."""
    score_request = ScoreRequest(
        party_id=party_id,
        total_score=result['total_score'],
        band=result['band'],
        scorecard_version=result['scorecard_version'],
        request_metadata={
            'components': result['components'],
            'rules_applied': result['rules_applied'],
            'computed_at': result['computed_at']
        }
    )
    self.db.add(score_request)
    self.db.commit()
```

---

## Batch Scoring

For scoring multiple parties:

```python
def score_batch(self, batch_id: str, scorecard_version: str = "v1") -> dict:
    """
    Score all parties in a batch.
    
    Returns:
        dict with batch_id, scored_count, results
    """
    parties = self.db.query(Party).filter(Party.batch_id == batch_id).all()
    
    results = []
    for party in parties:
        try:
            result = self.compute_score(party.id, scorecard_version=scorecard_version)
            results.append(result)
        except Exception as e:
            results.append({
                'party_id': party.id,
                'error': str(e),
                'total_score': None
            })
    
    return {
        'batch_id': batch_id,
        'scored_count': len([r for r in results if r.get('total_score')]),
        'error_count': len([r for r in results if r.get('error')]),
        'results': results
    }
```

---

## Score Explanation Generation

```python
def _generate_explanation(self, score_result: dict, rules_result: dict) -> str:
    """Generate human-readable score explanation."""
    explanation_parts = []
    
    # Top contributing factors
    components = sorted(
        score_result['components'],
        key=lambda x: x['contribution'],
        reverse=True
    )[:3]
    
    for comp in components:
        pct = (comp['contribution'] / comp['max_contribution']) * 100
        explanation_parts.append(
            f"{comp['feature']}: {pct:.0f}% of maximum"
        )
    
    # Rules applied
    if rules_result.get('rules_applied'):
        explanation_parts.append(
            f"Rules applied: {', '.join(rules_result['rules_applied'])}"
        )
    
    return "; ".join(explanation_parts)
```

---

## Performance Optimization

### Caching

Features are cached to avoid recomputation:

```python
from app.cache.ttl_cache import feature_cache

def compute_score_cached(self, party_id: int, **kwargs) -> dict:
    cache_key = f"party:{party_id}:score"
    
    cached = feature_cache.get(cache_key)
    if cached:
        return cached
    
    result = self.compute_score(party_id, **kwargs)
    feature_cache.set(cache_key, result, ttl=300)
    
    return result
```

### Parallel Feature Extraction

Extractors can run in parallel:

```python
from concurrent.futures import ThreadPoolExecutor

def extract_features_parallel(self, party_id: int) -> list:
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = [
            executor.submit(ext.extract, party_id, self.db)
            for ext in self.extractors
        ]
        results = [f.result() for f in futures]
    return [item for sublist in results for item in sublist]
```

---

## Error Handling

```python
def compute_score_safe(self, party_id: int, **kwargs) -> dict:
    """Compute score with error handling."""
    try:
        return self.compute_score(party_id, **kwargs)
    except PartyNotFoundError:
        return {
            'party_id': party_id,
            'error': 'Party not found',
            'total_score': None
        }
    except FeatureExtractionError as e:
        return {
            'party_id': party_id,
            'error': f'Feature extraction failed: {e}',
            'total_score': None
        }
    except Exception as e:
        return {
            'party_id': party_id,
            'error': f'Unexpected error: {e}',
            'total_score': None
        }
```
