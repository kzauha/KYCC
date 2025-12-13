# Synthetic Data Generation Guide

## Overview

KYCC includes a sophisticated synthetic data generator that creates realistic B2B supply chain entities, relationships, and transactions for testing and demonstration purposes.

## Features

- **Risk-based profiles**: excellent, good, fair, poor (aligned with 300-900 credit scoring bands)
- **Supply chain topology**: Supplier → Manufacturer → Distributor → Retailer → Customer
- **Realistic patterns**: Transaction volumes, amounts, and regularity correlate with risk profiles
- **Network diversity**: Excellent companies have 8-15 suppliers; poor companies have 1-3
- **Currency**: All amounts in NRS (Nepalese Rupees)

---

## Quick Start

### 1. Generate Synthetic Data

```powershell
cd backend

# Generate 100 companies (balanced risk distribution)
python -m scripts.seed_synthetic_profiles \
    --batch-id BATCH_001 \
    --count 100 \
    --scenario balanced \
    --seed 42 \
    --out data/synthetic_profiles.json
```

**Output**:
```
✅ Generation Complete!
   Parties: 100
   Accounts: 100
   Transactions: 10,827
   Relationships: 668

Profile Breakdown:
   excellent :   15 ( 15.0%)
   good      :   35 ( 35.0%)
   fair      :   35 ( 35.0%)
   poor      :   15 ( 15.0%)
```

### 2. Load into Database

```powershell
cd backend
python ingest_data.py
```

**Output**:
```
✅ Ingestion Complete!
   Parties: 100
   Accounts: 100
   Transactions: 10,827
   Relationships: 668
```

---

## Risk Profile Distribution

### Scenario: `balanced` (default)
- 15% excellent (900-1000 score range)
- 35% good (800-899)
- 35% fair (700-799)
- 15% poor (600-699)

### Scenario: `risky`
- 5% excellent
- 20% good
- 40% fair
- 35% poor

### Scenario: `safe`
- 30% excellent
- 45% good
- 20% fair
- 5% poor

---

## Profile Characteristics

### Excellent Companies
```
KYC:
✓ 100% KYC verified
✓ 100% have tax ID
✓ 90-100% contact info complete
✓ 8-25 years old
✓ Mostly manufacturers & distributors

Transactions (6 months):
✓ 150-300 transactions
✓ NPR 30,000-80,000 avg amount
✓ 85-100% regularity score
✓ 3 payment types used
✓ 100% recent activity

Network:
✓ 8-15 suppliers
✓ 15-40 customers
✓ 4-7 network depth

Balance: NPR 100,000-500,000
```

### Good Companies
```
KYC:
✓ 100% verified
✓ 75-95% contact complete
✓ 4-12 years old

Transactions:
✓ 80-180 transactions
✓ NPR 15,000-50,000 avg
✓ 70-90% regularity

Network:
✓ 4-10 suppliers
✓ 8-25 customers

Balance: NPR 30,000-150,000
```

### Fair Companies
```
KYC:
⚠ 60% verified
⚠ 50-80% contact complete
⚠ 1.5-6 years old

Transactions:
⚠ 30-100 transactions
⚠ NPR 5,000-25,000 avg
⚠ 40-75% regularity

Network:
⚠ 2-6 suppliers
⚠ 3-12 customers

Balance: NPR 5,000-40,000
```

### Poor Companies
```
KYC:
✗ 10% verified
✗ 20-60% contact complete
✗ 0.3-3 years old

Transactions:
✗ 5-40 transactions
✗ NPR 1,000-10,000 avg
✗ 10-50% regularity

Network:
✗ 1-3 suppliers
✗ 1-5 customers

Balance: NPR 500-8,000
```

---

## Relationship Generation

### Supply Chain Topology

```
Supplier (15-20 parties)
    |
    | supplies_to
    ↓
Manufacturer (10-15 parties)
    |
    | manufactures_for
    ↓
Distributor (15-20 parties)
    |
    | distributes_for
    ↓
Retailer (20-30 parties)
    |
    | sells_to
    ↓
Customer (20-30 parties)
```

### Cross-Connections
- Supplier → Distributor (direct sourcing, skip manufacturer)
- Manufacturer → Retailer (direct-to-retail, skip distributor)

### Profile Mixing
Relationships are **type-based, not profile-based**:
- An excellent distributor may supply to a fair retailer
- A poor supplier may connect to a good manufacturer
- Profile determines **connection count**, not **who connects to whom**

---

## Transaction Patterns

### Types
1. **invoice** (60% of positive transactions) - Bills sent
2. **payment** (40% of positive transactions) - Money received
3. **credit_note** (5-40% based on profile) - Refunds/returns

### Amount Distribution
- **Volatility coefficient**: 0.15 (excellent) to 0.70 (poor)
- **Base amounts**: NPR 1,000 to NPR 80,000
- **Negative amounts**: Credit notes have negative values

### Date Distribution
- **Recent activity**: Excellent = 100% have txns in last 30 days
- **Poor activity**: Poor = 30% have recent txns
- **Date range**: Last 180 days

---

## Command Reference

### Generate with Custom Settings

```powershell
# Risky portfolio (more poor companies)
python -m scripts.seed_synthetic_profiles \
    --batch-id BATCH_002 \
    --count 200 \
    --scenario risky \
    --seed 123 \
    --out data/risky_profiles.json

# Safe portfolio (more excellent companies)
python -m scripts.seed_synthetic_profiles \
    --batch-id BATCH_003 \
    --count 50 \
    --scenario safe \
    --seed 456 \
    --out data/safe_profiles.json
```

### Regenerate with Same Seed (Reproducible)

```powershell
# Same seed = identical data generation
python -m scripts.seed_synthetic_profiles \
    --batch-id BATCH_001 \
    --count 100 \
    --scenario balanced \
    --seed 42 \
    --out data/synthetic_profiles.json
```

### Ingest with Overwrite

The `ingest_data.py` script automatically:
1. Cleans existing batch data (DELETE WHERE batch_id = 'BATCH_001')
2. Loads new data (INSERT)
3. Maintains referential integrity (relationships → transactions → accounts → parties)

---

## Database Schema Impact

### Tables Populated
- `parties` - 100 records (business entities)
- `accounts` - 100 records (1 per party)
- `transactions` - ~10,000 records (invoices, payments, credit notes)
- `relationships` - ~650 records (supply chain edges)

### Tables NOT Populated (Generated During Scoring)
- `features` - Empty until feature extraction runs
- `score_requests` - Empty until scoring API called
- `credit_scores` - Legacy table (may be removed)

---

## Architecture

### File Structure
```
backend/
├── scripts/
│   └── seed_synthetic_profiles.py  # Generator script
├── app/
│   ├── config/
│   │   └── synthetic_mapping.py     # Type mappings
│   ├── services/
│   │   └── synthetic_seed_service.py # DB ingestion
│   └── adapters/
│       └── synthetic_adapter.py     # Data adapter
├── data/
│   └── synthetic_profiles.json      # Generated output
├── ingest_data.py                   # Ingestion script
└── inspect_db.py                    # Database viewer
```

### Data Flow
```
1. seed_synthetic_profiles.py
   ↓ (generates JSON)
2. data/synthetic_profiles.json
   ↓ (loaded by)
3. ingest_data.py → synthetic_seed_service.py
   ↓ (applies mappings)
4. synthetic_mapping.py
   ↓ (converts to enums)
5. SQLAlchemy models
   ↓ (persists to)
6. PostgreSQL database
```

---

## Customization

### Add New Profile

Edit `backend/scripts/seed_synthetic_profiles.py`:

```python
PROFILE_CONFIGS = {
    "excellent": ProfileConfig(...),
    "good": ProfileConfig(...),
    "fair": ProfileConfig(...),
    "poor": ProfileConfig(...),
    "stellar": ProfileConfig(  # NEW
        name="stellar",
        kyc_verified_prob=1.0,
        txn_count_6m_range=(300, 500),  # Higher volume
        balance_range=(500000, 1000000),  # Larger balance
        # ... other settings
    )
}
```

### Modify Party Types

Edit `backend/app/config/synthetic_mapping.py`:

```python
PARTY_TYPE_MAP = {
    "supplier": "supplier",
    "vendor": "supplier",  # Alias
    "contractor": "supplier",  # NEW mapping
    # ...
}
```

### Change Currency

Edit `backend/scripts/seed_synthetic_profiles.py`:

```python
# Line 386 and 518
"currency": "USD",  # Change to "EUR", "GBP", etc.
```

---

## Verification Commands

### Check Record Counts
```powershell
cd backend
python -c "from app.db.database import SessionLocal; from app.models.models import Party, Transaction, Relationship; db=SessionLocal(); print(f'Parties: {db.query(Party).count()}'); print(f'Transactions: {db.query(Transaction).count()}'); print(f'Relationships: {db.query(Relationship).count()}'); db.close()"
```

### Inspect Sample Data
```powershell
cd backend
python inspect_db.py
```

### Check Currency
```powershell
cd backend
python -c "from app.db.database import SessionLocal; from app.models.models import Account; db=SessionLocal(); acc=db.query(Account).first(); print(f'Currency: {acc.currency}'); db.close()"
```

---

## Known Limitations

1. **No historical trends**: All transactions within 180-day window
2. **Simplified fraud patterns**: No explicit fraud/default scenarios
3. **Static party types**: No business evolution (supplier becoming manufacturer)
4. **No seasonality**: Transaction patterns don't reflect seasonal business cycles
5. **No external shocks**: No modeling of economic downturns, supply disruptions

Future versions may address these limitations.

---

## Troubleshooting

### "Module not found" error
```powershell
# Ensure you're in backend directory
cd backend
python -m scripts.seed_synthetic_profiles ...
```

### "Database schema mismatch"
```powershell
# Run migrations
cd backend
alembic upgrade head
```

### "Port already in use"
```powershell
# Use different port or kill process
netstat -ano | findstr :8000
taskkill /PID <pid> /F
```

### "JSON file not found"
```powershell
# Check file exists
dir backend\data\synthetic_profiles.json

# Regenerate if missing
python -m scripts.seed_synthetic_profiles --batch-id BATCH_001 --count 100 --out data/synthetic_profiles.json
```
