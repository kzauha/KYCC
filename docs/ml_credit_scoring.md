# Machine Learning Credit Scoring in KYCC

## What Problem the Model Solves

KYCC (Know Your Customer's Customer) helps businesses assess the credit risk of their trading partners — suppliers, manufacturers, distributors, and retailers in a supply chain. The ML model predicts whether a party is likely to default on payments.

**What this means**: The model looks at a party's KYC information, transaction history, and network connections, then outputs a score indicating default risk. Higher risk = more likely to fail to pay.

**How the score is used**: In the product, scores help users prioritize which parties need closer monitoring, set credit limits, or decide whether to extend payment terms. Scores range from 300-900 (like FICO), with bands like "excellent," "good," "fair," and "poor."

---

## High-Level ML Flow (End-to-End)

**Step 1: Data Ingestion**  
Raw business data (parties, transactions, relationships) is loaded into the KYCC database from various sources (synthetic files, ERP integrations, manual uploads).

**Step 2: Feature Extraction**  
The system computes numeric features from raw tables — things like "how many transactions in the last 6 months" or "how complete is their KYC profile."

**Step 3: Feature Matrix Assembly**  
Features and ground-truth labels (did they default?) are combined into a training dataset with rows = parties and columns = features + label.

**Step 4: Model Training**  
A logistic regression model learns patterns from labeled historical data, identifying which features correlate with default risk.

**Step 5: Model Evaluation**  
The trained model is tested on unseen parties to measure how well it predicts defaults using metrics like AUC and F1 score.

**Step 6: Model Persistence**  
The trained model and its performance metrics are saved to the `ModelRegistry` table for versioning and deployment.

**Step 7: Scoring New Parties**  
When a new party is scored, their features are extracted, passed through the active model, and a 300-900 score is generated.

---

## Data Sources in KYCC

### `parties` Table
**What it represents**: Companies or individuals in the supply chain (suppliers, manufacturers, distributors, retailers, customers).

**Why it matters**: This is the entity being scored. Their KYC completeness, age, and party type influence creditworthiness.

**Key info**: Company registration details, tax IDs, contact information, verification status.

### `transactions` Table
**What it represents**: Financial transactions between parties — invoices, payments, credit notes.

**Why it matters**: Transaction volume, regularity, and recency signal financial health and activity levels.

**Key info**: Transaction dates, amounts, transaction types, counterparties.

### `relationships` Table
**What it represents**: Business connections between parties (who supplies to whom, who manufactures for whom).

**Why it matters**: Network depth and diversity indicate stability — parties with strong networks are often lower risk.

**Key info**: Relationship types (supplies_to, distributes_for), establishment dates, network structure.

### `accounts` Table
**What it represents**: Bank accounts tied to parties.

**Why it matters**: Account balances and currency usage provide financial context.

**Key info**: Account numbers, balances, currencies, account types.

### `features` Table
**What it represents**: Computed numeric features derived from raw data, versioned over time.

**Why it matters**: This is the ML pipeline's intermediate storage — features are computed once and reused for training and scoring.

**Key info**: Feature names, values, computation timestamps, validity periods (`valid_from`, `valid_to`).

### `ground_truth_labels` Table
**What it represents**: Historical labels indicating whether a party defaulted (1) or not (0).

**Why it matters**: This is the "answer key" the model learns from during training.

**Key info**: `will_default` (binary), `risk_level` (high/medium/low), label source (synthetic/manual/historical), dataset batch ID.

### `model_registry` Table
**What it represents**: Trained models with their configurations, performance metrics, and deployment status.

**Why it matters**: Tracks model versions, enables rollback, and ensures only validated models are used for scoring.

**Key info**: Model name/version, algorithm config (weights, hyperparams), training batch ID, AUC/F1/precision/recall, `is_active` flag.

---

## Schemas & Key Fields

### Party → Feature Linkage
`Party.id` → `Feature.party_id`  
Every party can have multiple features over time; use `Feature.valid_to IS NULL` to get current features.

### Party → Label Linkage
`Party.id` → `GroundTruthLabel.party_id` (one-to-one)  
Each party has at most one ground truth label per dataset batch.

### Party → Transaction Linkage
`Party.id` → `Transaction.party_id` (one-to-many)  
Parties have many transactions as either the main party or counterparty.

### Party → Relationship Linkage
`Party.id` → `Relationship.from_party_id` or `Relationship.to_party_id`  
Parties have upstream (suppliers) and downstream (customers) relationships.

### Key Assumptions
- **Batch isolation**: Training data is scoped by `batch_id` to avoid mixing datasets (e.g., `BATCH_001` for synthetic profiles).
- **Feature currency**: Only features with `valid_to IS NULL` are "current" and used for scoring.
- **Label validity**: Labels are assumed correct for the labeled dataset; in production, labels come from actual payment outcomes.

---

## Feature Engineering

### What a "Feature" Means in KYCC
A feature is a numeric value derived from raw data that helps the model predict default risk. For example, "number of transactions in the last 6 months" is a feature. Each party gets a feature vector (set of features) that the model uses.

### Concrete Examples

**From KYC Data (KYCFeatureExtractor)**:
- `kyc_verified`: 0 or 1 — whether the party passed identity verification. Unverified parties are riskier.
- `company_age_years`: How long the company has existed. Older companies are often more stable.
- `party_type_score`: Numeric encoding of party type (manufacturer=10, distributor=8, etc.). Different roles have different risk profiles.
- `contact_completeness`: % of contact fields filled (email, phone, address). Complete profiles signal professionalism.
- `has_tax_id`: 0 or 1 — whether a tax ID is on file. Missing tax IDs are red flags.

**From Transaction Data (TransactionFeatureExtractor)**:
- `transaction_count_6m`: Total transactions in the last 6 months. Low activity = higher risk.
- `avg_transaction_amount`: Average transaction size. Helps assess scale and consistency.
- `transaction_regularity_score`: How consistent monthly transaction volumes are. Irregular activity is risky.

**From Network Data (NetworkFeatureExtractor)**:
- `network_size`: Total unique parties in the network graph. Larger networks = more connections = lower risk.
- `direct_counterparty_count`: Number of direct suppliers/customers. Diversification reduces risk.
- `network_depth_downstream`: How many hops to the furthest customer. Deeper networks indicate reach.

### Why Each Feature Exists
Features are chosen to capture different dimensions of creditworthiness:
- **Stability**: Company age, KYC completeness → Are they established?
- **Activity**: Transaction volume, recency → Are they active?
- **Reliability**: Payment regularity → Are they consistent?
- **Connections**: Network size, counterparty count → Are they integrated?

### What Can Go Wrong
- **Missing features**: If extractors fail, features are imputed as 0.0. This can bias scores downward.
- **Stale features**: If `valid_to` isn't properly managed, old features might be used.
- **Data quality issues**: Garbage in = garbage out. If transaction dates are wrong or relationships are incomplete, features will be misleading.

---

## Labels & Ground Truth

### Where Labels Come From

**Current state**: Labels are derived from synthetic profile assignments:
- Synthetic profiles (`excellent`, `good`, `fair`, `poor`) are mapped to risk levels and default flags.
- `poor` → `risk_level: high`, `will_default: 1`
- `fair` → `risk_level: medium`, `will_default: 0`
- `good`/`excellent` → `risk_level: low`, `will_default: 0`

**Future state**: In production, labels would come from:
- Actual payment outcomes (did the party default within 90 days?)
- Manual risk assessments by credit analysts
- Historical collections data

### Why Labels Are Imperfect

**Synthetic labels are simplified**: They assume `poor` profiles always default and `fair`/`good` never do. Reality is messier — even "good" parties can default under stress.

**Temporal mismatch**: Labels are static snapshots. Real default risk evolves over time as business conditions change.

**Class imbalance**: Default events are rare (typically <5% of parties). Our synthetic data may not reflect this imbalance.

### What the Model Is Actually Learning

Because of synthetic labels, the model is learning to distinguish **profile archetypes** (low KYC + irregular transactions = high risk) rather than true default predictors. This is useful for pipeline validation but not ready for real-world credit decisions.

---

## The Model Itself

### Why Logistic Regression Was Chosen

**Interpretability**: Coefficients show exactly how each feature affects risk. You can explain to stakeholders why a score changed.

**Speed**: Trains in seconds, scores in milliseconds. No GPU required.

**Baseline**: Establishes a simple, transparent baseline before trying complex models (XGBoost, neural nets).

**Regulatory compliance**: Explainability is critical for credit scoring; "black box" models face legal hurdles.

### What Inputs It Takes

The model takes a feature vector per party:
```
X = [kyc_verified, company_age_years, party_type_score, contact_completeness, 
     has_tax_id, transaction_count_6m, avg_transaction_amount, 
     transaction_regularity_score, network_size]
```

Each value is normalized (typically 0-1 range via Min-Max scaling) before training.

### What Output It Produces

The model outputs:
- **Probability**: `P(default = 1)` — a value between 0 and 1 indicating default likelihood.
- **Raw score**: Converted to a 300-900 scale (higher = lower risk).
- **Score band**: Bucketed into "excellent," "good," "fair," "poor" based on thresholds.

### What the Score Represents (and Does NOT Represent)

**Represents**:
- Relative risk ranking: A score of 800 is lower risk than 600.
- Feature-based assessment: The score reflects patterns in KYC, transactions, and network.

**Does NOT represent**:
- Absolute default probability: A 700 score doesn't mean "30% chance of default."
- Future behavior: The model is backward-looking; it can't predict black swan events.
- Causation: Correlation ≠ causation. Low KYC might correlate with default, but improving KYC doesn't guarantee solvency.

---

## Training Process

### Step-by-Step (Concrete and KYCC-Specific)

**1. Data Extraction**  
Query the database for all parties in a specific batch (e.g., `BATCH_001`):
```python
parties = db.query(Party).filter(Party.batch_id == batch_id).all()
```

**2. Feature Computation**  
For each party, run extractors:
- `KYCFeatureExtractor` → reads `Party` table
- `TransactionFeatureExtractor` → reads `Transaction` table
- `NetworkFeatureExtractor` → reads `Relationship` table

Features are stored in the `features` table with `valid_to IS NULL` for current values.

**3. Dataset Assembly**  
Build the feature matrix:
- Fetch current features for each party
- Join with `GroundTruthLabel` on `party_id`
- Drop parties without labels (can't train without `y`)
- Impute missing features with 0.0
- Result: `X` (DataFrame of features) and `y` (Series of labels)

**4. Train/Test Split**  
Split 80/20 stratified by label:
```python
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, stratify=y)
```
Stratification ensures both splits have similar default rates.

**5. Model Training**  
Train logistic regression on `X_train, y_train`:
```python
model = LogisticRegression(max_iter=200, random_state=42)
model.fit(X_train, y_train)
```

**6. Basic Evaluation**  
Predict on `X_test` and compute metrics:
- **AUC-ROC**: Measures the model's ability to rank risky parties higher than safe ones (0.5 = random, 1.0 = perfect).
- **F1 Score**: Balances precision (% of predicted defaults that are correct) and recall (% of actual defaults caught).
- **Confusion Matrix**: True positives, false positives, true negatives, false negatives.

**7. Conversion to Scorecard**  
Convert ML coefficients to interpretable scorecard points:
```python
# Coefficients: [0.5, -0.3, 0.8, 0.2, 0.1] (raw weights)
# ↓ Normalize to points scale
# Scorecard: {kyc_verified: 25, company_age: -15, party_type: 40, ...}
scorecard_config = trainer.convert_to_scorecard(model, feature_names)
```

**Why convert to scorecard?**
- **Interpretable**: "You lost 15 points for low transaction count"
- **Explainable**: Auditors and regulators can understand the logic
- **Industry standard**: Most credit scoring systems use point-based scorecards

**8. Persistence**  
Save the scorecard (not raw ML model) to `ModelRegistry`:
```python
registry_info = trainer.save_as_scorecard(
    model=model,
    metrics=metrics,
    model_version="v1",
    training_data_batch_id=batch_id,
    set_active=True
)
```

The stored config looks like:
```json
{
  "model_type": "scorecard",
  "weights": {
    "kyc_verified": 25,
    "company_age_years": -15,
    "party_type_score": 40,
    ...
  },
  "intercept": 50,
  "features": ["kyc_verified", ...]
}
```

---

## Current State of the Project

### What Is Already Implemented

✅ **Data ingestion**: Synthetic profiles can be loaded into Postgres via `ingest_seed_file()`.  
✅ **Feature extraction**: Three extractors (KYC, Transaction, Network) compute features and store them in the `features` table.  
✅ **Feature pipeline service**: Orchestrates extractors, manages feature versioning (`valid_from`/`valid_to`).  
✅ **Ground truth labels**: Auto-created during synthetic ingest based on profile risk levels.  
✅ **Feature matrix builder**: Combines features + labels into training-ready `X, y` DataFrames with train/test splits.  
✅ **Model training service**: Trains logistic regression, evaluates metrics (AUC, F1), and returns trained models.  
✅ **Dagster orchestration**: Pipeline `training_pipeline` with `build_matrix_op` and `train_and_evaluate_op` jobs.  
✅ **Database schema**: `ModelRegistry` and `ModelExperiment` tables for tracking models.

### What Is Partially Implemented

⚠️ **Feature validation**: `FeatureValidationService` exists but isn't enforced before training.  
⚠️ **Performance monitoring**: No drift detection, no ongoing evaluation, no alerts.

### What Is Now Complete

✅ **ML-Refined Scorecard**: Training produces an ML model, which is automatically converted to an interpretable scorecard format before saving to the registry.  
✅ **Model persistence**: The `save_as_scorecard()` method converts coefficients to points and stores them in `ModelRegistry`.  
✅ **Unified scoring**: `ScoringService` uses the stored scorecard weights directly - no separate ML inference path needed.



### Known Limitations

- **Synthetic data only**: Model is trained on generated profiles, not real business data.
- **Class imbalance not addressed**: No SMOTE, class weighting, or sampling strategies.
- **Feature imputation is naive**: Missing features default to 0.0, which may bias scores.
- **No temporal validation**: Model uses point-in-time splits, not time-based splits (which are critical for credit scoring).
- **Batch-scoped training**: Each batch is isolated; no cross-batch learning or transfer learning.

## Purpose

**This model is primarily for pipeline validation, not decision automation.**

Why? Because:
- **Synthetic labels are toy data**: They reflect profile archetypes, not real default events. A model trained on synthetic data cannot make reliable predictions about real parties.

**What the model IS good for**:
- **Proving the pipeline works**: End-to-end flow from raw data → features → training → evaluation → persistence.

---

## How to Monitor & Verify

### 1. View Pipeline in Dagster
The Dagster UI visualizes the entire training pipeline.

1. Open **[Dagster UI](http://localhost:3000)** in your browser.
2. Navigate to **Assets** or **Jobs**.
3. Select `training_pipeline` or filter for assets like `build_training_matrix` and `register_model`.
4. Click **Materialize** to manually trigger a run.
5. Watch the logs to see:
   - Feature matrix construction (row counts)
   - Model training metrics (AUC, F1)
   - Scorecard conversion (weights)

### 2. Inspect Trained Models (Database)
Connect to your PostgreSQL database to see registered scorecards:

```sql
SELECT 
    model_version, 
    model_type, 
    training_date, 
    performance_metrics->>'roc_auc' as auc 
FROM model_registry 
ORDER BY training_date DESC;
```

To see the actual scorecard weights:
```sql
SELECT model_config FROM model_registry ORDER BY training_date DESC LIMIT 1;
```

### 3. View Scoring History
See the scores generated for parties:

```sql
SELECT 
    created_at, 
    party_id, 
    final_score, 
    score_band, 
    decision 
FROM score_requests 
ORDER BY created_at DESC;
```
