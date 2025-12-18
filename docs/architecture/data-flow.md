# Data Flow

This document describes how data flows through the KYCC system from ingestion to scoring.

## Overview

Data flows through KYCC in several distinct pathways:

1. **Scoring Flow**: Real-time score computation for a party
2. **Batch Flow**: Processing multiple parties through the Dagster pipeline
3. **Training Flow**: ML model training on historical data

---

## Scoring Flow

When a score is requested for a party, data flows through these stages:

```
┌─────────────────────────────────────────────────────────────────────┐
│                         API Request                                 │
│              GET /api/scoring/run?party_id=123                      │
└─────────────────────────────────────┬───────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      ScoringService                                 │
│                  compute_score(party_id=123)                        │
└─────────────────────────────────────┬───────────────────────────────┘
                                      │
          ┌───────────────────────────┼───────────────────────────┐
          │                           │                           │
          ▼                           ▼                           ▼
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│ KYC Extractor   │       │ Txn Extractor   │       │ Network Extract │
│                 │       │                 │       │                 │
│ Party Table     │       │ Transaction Tbl │       │ Relationship Tbl│
│ ↓               │       │ ↓               │       │ ↓               │
│ kyc_verified    │       │ txn_count_6m    │       │ network_size    │
│ company_age     │       │ avg_amount      │       │ counterparties  │
│ party_type      │       │ regularity      │       │ depth           │
└────────┬────────┘       └────────┬────────┘       └────────┬────────┘
         │                         │                         │
         └─────────────────────────┼─────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      Feature Store                                  │
│              features table (party_id=123)                          │
│                                                                     │
│  feature_name          | feature_value | valid_from    | valid_to   │
│  ──────────────────────┼───────────────┼───────────────┼──────────  │
│  kyc_verified          | 1.0           | 2024-01-01    | NULL       │
│  company_age_years     | 3.5           | 2024-01-01    | NULL       │
│  transaction_count_6m  | 45.0          | 2024-01-01    | NULL       │
│  network_size          | 12.0          | 2024-01-01    | NULL       │
└─────────────────────────────────┬───────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    Scorecard Engine                                 │
│                                                                     │
│  base_score = 300                                                   │
│  + kyc_verified * 15     = 15                                       │
│  + company_age * 10      = 35 (capped at 5 years)                   │
│  + txn_count_6m * 20     = 180 (capped at 50)                       │
│  + network_size * 10     = 60 (capped at 20)                        │
│  ────────────────────────────────                                   │
│  raw_score = 590                                                    │
│  final_score = max(300, min(900, 590)) = 590                        │
└─────────────────────────────────┬───────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    Score Request (Audit)                            │
│                                                                     │
│  id: req_123_batch_001                                              │
│  party_id: 123                                                      │
│  final_score: 590                                                   │
│  score_band: fair                                                   │
│  features_snapshot: {kyc_verified: 1.0, ...}                        │
│  model_version: scorecard_v1.0                                      │
└─────────────────────────────────┬───────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      API Response                                   │
│  {                                                                  │
│    "party_id": 123,                                                 │
│    "total_score": 590,                                              │
│    "band": "fair",                                                  │
│    "confidence": 0.85,                                              │
│    "explanation": {...}                                             │
│  }                                                                  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Batch Processing Flow

The Dagster pipeline processes entire batches:

```
┌─────────────────────────────────────────────────────────────────────┐
│              Stage 1: Ingestion                                     │
│                                                                     │
│  BATCH_001_profiles.json                                            │
│         │                                                           │
│         ▼                                                           │
│  ingest_synthetic_batch                                             │
│         │                                                           │
│         ▼                                                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                 │
│  │   parties   │  │transactions │  │relationships│                 │
│  │   table     │  │   table     │  │    table    │                 │
│  └─────────────┘  └─────────────┘  └─────────────┘                 │
└─────────────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────────┐
│              Stage 2: Feature Extraction                            │
│                                                                     │
│     ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │
│     │ kyc_features │  │txn_features  │  │net_features  │           │
│     └──────┬───────┘  └──────┬───────┘  └──────┬───────┘           │
│            │                 │                 │                    │
│            └─────────────────┼─────────────────┘                    │
│                              ▼                                      │
│                       features_all                                  │
│                              │                                      │
│                              ▼                                      │
│                    ┌─────────────────┐                              │
│                    │  features table │                              │
│                    │ (all parties)   │                              │
│                    └─────────────────┘                              │
└─────────────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────────┐
│              Stage 3: Scoring                                       │
│                                                                     │
│                      score_batch                                    │
│                          │                                          │
│     For each party:      │                                          │
│     ┌────────────────────┼────────────────────┐                    │
│     │ Load features      │                    │                    │
│     │ Apply scorecard    │                    │                    │
│     │ Save ScoreRequest  │                    │                    │
│     └────────────────────┼────────────────────┘                    │
│                          │                                          │
│                          ▼                                          │
│               ┌─────────────────────┐                               │
│               │  score_requests     │                               │
│               │  (all parties)      │                               │
│               └─────────────────────┘                               │
└─────────────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────────┐
│              Stage 4: Label Generation                              │
│                                                                     │
│                generate_scorecard_labels                            │
│                          │                                          │
│     For each party:      │                                          │
│     ┌────────────────────┼────────────────────┐                    │
│     │ Get score          │                    │                    │
│     │ Apply threshold    │                    │                    │
│     │ Create label       │                    │                    │
│     └────────────────────┼────────────────────┘                    │
│                          │                                          │
│                          ▼                                          │
│               ┌─────────────────────┐                               │
│               │ ground_truth_labels │                               │
│               │ (will_default 0/1)  │                               │
│               └─────────────────────┘                               │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Training Flow

ML model training uses labeled historical data:

```
┌─────────────────────────────────────────────────────────────────────┐
│              Stage 5: Training Preparation                          │
│                                                                     │
│                  build_training_matrix                              │
│                          │                                          │
│     ┌────────────────────┼────────────────────┐                    │
│     │                    │                    │                    │
│     ▼                    ▼                    ▼                    │
│  features           ground_truth_labels    validation             │
│     │                    │                    │                    │
│     └────────────────────┼────────────────────┘                    │
│                          │                                          │
│                          ▼                                          │
│              ┌───────────────────────┐                              │
│              │   Training Matrix     │                              │
│              │   X: features         │                              │
│              │   y: will_default     │                              │
│              │   train/test split    │                              │
│              └───────────────────────┘                              │
└─────────────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────────┐
│              Stage 6: Model Training                                │
│                                                                     │
│                   train_model_asset                                 │
│                          │                                          │
│     ┌────────────────────┼────────────────────┐                    │
│     │ Logistic Regression                     │                    │
│     │ - balanced class weights                │                    │
│     │ - L2 regularization                     │                    │
│     │ - feature scaling                       │                    │
│     └────────────────────┼────────────────────┘                    │
│                          │                                          │
│                          ▼                                          │
│               ┌─────────────────────┐                               │
│               │  Trained Model      │                               │
│               │  - coefficients     │                               │
│               │  - scaler           │                               │
│               │  - metrics          │                               │
│               └─────────────────────┘                               │
└─────────────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────────┐
│              Stage 7: Scorecard Refinement                          │
│                                                                     │
│                    refine_scorecard                                 │
│                          │                                          │
│     ┌────────────────────┼────────────────────┐                    │
│     │ Extract weights from coefficients       │                    │
│     │ Apply quality gates:                    │                    │
│     │   - AUC >= 0.55                         │                    │
│     │   - Improvement >= 0.5%                 │                    │
│     └────────────────────┼────────────────────┘                    │
│                          │                                          │
│              ┌───────────┴───────────┐                              │
│              │                       │                              │
│              ▼                       ▼                              │
│       Passes Gates            Fails Gates                          │
│              │                       │                              │
│              ▼                       ▼                              │
│    ┌─────────────────┐    ┌─────────────────┐                      │
│    │ New Version     │    │ Failed Version  │                      │
│    │ status: active  │    │ status: failed  │                      │
│    │ (retire old)    │    │ (for review)    │                      │
│    └─────────────────┘    └─────────────────┘                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Data Transformations

### Raw Data to Features

| Source | Raw Data | Feature | Transformation |
|--------|----------|---------|----------------|
| Party | `created_at` | `company_age_years` | `(now - created_at).days / 365.25` |
| Party | `kyc_verified` | `kyc_verified` | Direct boolean to float |
| Party | `tax_id` | `has_tax_id` | `1.0 if exists else 0.0` |
| Transaction | count | `transaction_count_6m` | Count where date >= 6 months ago |
| Transaction | amounts | `avg_transaction_amount` | `sum(amounts) / count` |
| Transaction | monthly volumes | `transaction_regularity_score` | `100 - (std/mean * 100)` |
| Relationship | count | `direct_counterparty_count` | Count upstream + downstream |
| Relationship | graph | `network_size` | Recursive traversal count |

### Features to Score

```
final_score = base_score + sum(
    scaled_feature_value * weight
    for feature, weight in scorecard.weights.items()
)

final_score = clip(final_score, 300, 900)
```

### Score to Band

| Score Range | Band |
|-------------|------|
| 750-900 | Excellent |
| 650-749 | Good |
| 500-649 | Fair |
| 300-499 | Poor |

---

## Cache Layer

Features are cached to avoid repeated extraction:

```
Request → Check Cache → Cache Hit? → Return cached features
                            │
                            ▼ Cache Miss
                     Extract features
                            │
                            ▼
                     Store in cache (TTL: 5 min)
                            │
                            ▼
                     Store in database
                            │
                            ▼
                     Return features
```

Cache key format: `party:{party_id}:features:all`
