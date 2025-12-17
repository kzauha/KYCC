"""Generate synthetic profiles (excellent/good/fair/poor) aligned with KYCC credit scoring.

Key improvements:
1. Uses 4 risk tiers matching credit score bands
2. Generates B2B supply chain entities (not individuals)
3. Transaction amounts and patterns reflect business reality
4. Network topology follows supply chain logic
5. Features correlate with scorecard weights

Usage:
    python -m backend.scripts.seed_synthetic_profiles \
        --batch-id BATCH123 \
        --out data/synthetic_profiles.json \
        --count 100
"""
from __future__ import annotations

import argparse
import json
import random
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Tuple

# Risk profiles aligned with credit score bands
RISK_PROFILES = ["excellent", "good", "fair", "poor"]

# B2B party types (supply chain)
PARTY_TYPES = ["supplier", "manufacturer", "distributor", "retailer", "customer"]

# Canonical transaction types from your backend
TXN_TYPES = ["invoice", "payment", "credit_note"]

# Canonical relationship types from your backend
REL_TYPES = ["supplies_to", "manufactures_for", "distributes_for", "sells_to"]


@dataclass
class ProfileConfig:
    """Configuration for each risk profile - drives data generation"""
    
    name: str
    
    # KYC Features
    kyc_verified_prob: float  # Probability of KYC verification
    has_tax_id_prob: float
    contact_completeness_range: Tuple[float, float]  # 0-100%
    company_age_years_range: Tuple[float, float]
    party_type_weights: Dict[str, float]  # Distribution of party types
    
    # Transaction Features
    txn_count_6m_range: Tuple[int, int]
    avg_txn_amount_range: Tuple[float, float]
    txn_regularity_score_range: Tuple[float, float]  # 0-100
    payment_type_diversity: int  # Number of distinct types used
    recent_activity_prob: float  # Probability of activity in last 30 days
    
    # Transaction behavior
    negative_amount_prob: float  # Credit notes, refunds
    txn_volatility: float  # Coefficient of variation in amounts
    payment_delay_prob: float  # Probability of late payment
    
    # Network Features
    supplier_count_range: Tuple[int, int]
    customer_count_range: Tuple[int, int]
    network_depth_range: Tuple[int, int]
    
    # Account/Balance
    balance_range: Tuple[float, float]
    account_type_weights: Dict[str, float]


# ============================================================================
# PROFILE CONFIGURATIONS - Based on scorecard weights
# ============================================================================

PROFILE_CONFIGS: Dict[str, ProfileConfig] = {
    "excellent": ProfileConfig(
        name="excellent",
        
        # KYC: Always verified, complete info
        kyc_verified_prob=1.0,
        has_tax_id_prob=1.0,
        contact_completeness_range=(90, 100),
        company_age_years_range=(8, 25),
        party_type_weights={"manufacturer": 0.4, "distributor": 0.3, "supplier": 0.3},
        
        # Transactions: High volume, regular, recent
        txn_count_6m_range=(150, 300),
        avg_txn_amount_range=(30000, 80000),
        txn_regularity_score_range=(85, 100),
        payment_type_diversity=3,
        recent_activity_prob=1.0,
        negative_amount_prob=0.05,  # Occasional credit notes
        txn_volatility=0.15,
        payment_delay_prob=0.02,
        
        # Network: Well-connected
        supplier_count_range=(8, 15),
        customer_count_range=(15, 40),
        network_depth_range=(4, 7),
        
        # Finance: Strong balances
        balance_range=(100000, 500000),
        account_type_weights={"checking": 0.7, "savings": 0.3},
    ),
    
    "good": ProfileConfig(
        name="good",
        
        kyc_verified_prob=1.0,
        has_tax_id_prob=1.0,
        contact_completeness_range=(75, 95),
        company_age_years_range=(4, 12),
        party_type_weights={"supplier": 0.3, "manufacturer": 0.3, "distributor": 0.4},
        
        txn_count_6m_range=(80, 180),
        avg_txn_amount_range=(15000, 50000),
        txn_regularity_score_range=(70, 90),
        payment_type_diversity=2,
        recent_activity_prob=0.95,
        negative_amount_prob=0.10,
        txn_volatility=0.25,
        payment_delay_prob=0.08,
        
        supplier_count_range=(4, 10),
        customer_count_range=(8, 25),
        network_depth_range=(3, 5),
        
        balance_range=(30000, 150000),
        account_type_weights={"checking": 0.8, "savings": 0.2},
    ),
    
    "fair": ProfileConfig(
        name="fair",
        
        kyc_verified_prob=0.6,  # Sometimes not verified
        has_tax_id_prob=0.7,
        contact_completeness_range=(50, 80),
        company_age_years_range=(1.5, 6),
        party_type_weights={"retailer": 0.4, "supplier": 0.3, "customer": 0.3},
        
        txn_count_6m_range=(30, 100),
        avg_txn_amount_range=(5000, 25000),
        txn_regularity_score_range=(40, 75),
        payment_type_diversity=1,
        recent_activity_prob=0.70,
        negative_amount_prob=0.20,
        txn_volatility=0.45,
        payment_delay_prob=0.20,
        
        supplier_count_range=(2, 6),
        customer_count_range=(3, 12),
        network_depth_range=(2, 4),
        
        balance_range=(5000, 40000),
        account_type_weights={"checking": 1.0},
    ),
    
    "poor": ProfileConfig(
        name="poor",
        
        kyc_verified_prob=0.1,  # Usually not verified
        has_tax_id_prob=0.3,
        contact_completeness_range=(20, 60),
        company_age_years_range=(0.3, 3),
        party_type_weights={"retailer": 0.5, "customer": 0.5},
        
        txn_count_6m_range=(5, 40),
        avg_txn_amount_range=(1000, 10000),
        txn_regularity_score_range=(10, 50),
        payment_type_diversity=1,
        recent_activity_prob=0.30,
        negative_amount_prob=0.40,  # Many refunds/disputes
        txn_volatility=0.70,
        payment_delay_prob=0.45,
        
        supplier_count_range=(1, 3),
        customer_count_range=(1, 5),
        network_depth_range=(1, 2),
        
        balance_range=(500, 8000),
        account_type_weights={"checking": 1.0},
    ),
}


# ============================================================================
# COMPANY NAME GENERATION
# ============================================================================

COMPANY_PREFIXES = [
    "Global", "United", "Premier", "Advanced", "Dynamic", "Innovative",
    "Strategic", "Superior", "Elite", "Prime", "Apex", "Vertex",
    "Pacific", "Atlantic", "Continental", "Metro", "Regional", "National"
]

COMPANY_SUFFIXES = {
    "supplier": ["Supply Co", "Materials Inc", "Resources Ltd", "Commodities Corp"],
    "manufacturer": ["Manufacturing", "Industries", "Production Corp", "Factory Ltd"],
    "distributor": ["Distribution", "Logistics Inc", "Supply Chain Co", "Wholesale Ltd"],
    "retailer": ["Retail Corp", "Stores Inc", "Markets Ltd", "Shops Co"],
    "customer": ["Enterprises", "Group", "Holdings", "Partners"]
}

CITIES = [
    "Shanghai", "Mumbai", "São Paulo", "Mexico City", "Cairo",
    "Bangkok", "Istanbul", "Lagos", "Jakarta", "Delhi",
    "Manila", "Seoul", "Karachi", "Buenos Aires", "Dhaka",
    "New York", "London", "Tokyo", "Singapore", "Dubai"
]


def generate_company_name(party_type: str, profile: str) -> str:
    """Generate realistic company name based on type"""
    prefix = random.choice(COMPANY_PREFIXES)
    suffix = random.choice(COMPANY_SUFFIXES.get(party_type, ["Corp", "Inc", "Ltd"]))
    return f"{prefix} {suffix}"


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _rand_date(days_back: int = 180) -> str:
    """Generate random ISO date within last N days"""
    now = datetime.utcnow()
    dt = now - timedelta(days=random.randint(0, days_back))
    return dt.isoformat() + "Z"


def _weighted_choice(weights: Dict[str, float]) -> str:
    """Choose randomly from weighted dict"""
    items = list(weights.keys())
    probs = list(weights.values())
    return random.choices(items, weights=probs)[0]


def _generate_transaction_amount(cfg: ProfileConfig, is_credit_note: bool = False) -> float:
    """Generate realistic transaction amount with volatility"""
    avg_min, avg_max = cfg.avg_txn_amount_range
    base_amount = random.uniform(avg_min, avg_max)
    
    # Apply volatility (coefficient of variation)
    volatility_factor = random.uniform(1 - cfg.txn_volatility, 1 + cfg.txn_volatility)
    amount = base_amount * volatility_factor
    
    # Credit notes are negative
    if is_credit_note or random.random() < cfg.negative_amount_prob:
        amount = -abs(amount)
    else:
        amount = abs(amount)
    
    return round(amount, 2)


def _generate_contact_info(completeness_pct: float, party_id: str) -> Dict[str, Any]:
    """Generate contact info based on completeness score"""
    fields = {}
    
    # Contact person
    if random.random() * 100 < completeness_pct:
        first_names = ["John", "Maria", "Wei", "Ahmed", "Sofia", "Raj", "Ana", "Chen"]
        last_names = ["Smith", "Garcia", "Chen", "Khan", "Silva", "Patel", "Lee", "Wang"]
        fields["contact_person"] = f"{random.choice(first_names)} {random.choice(last_names)}"
    
    # Email
    if random.random() * 100 < completeness_pct:
        fields["email"] = f"contact.{party_id.lower().replace('-', '')}@example.com"
    
    # Phone
    if random.random() * 100 < completeness_pct:
        fields["phone"] = f"+{random.randint(1, 999)}-{random.randint(100, 999)}-{random.randint(1000, 9999)}"
    
    # Address
    if random.random() * 100 < completeness_pct:
        street_num = random.randint(1, 9999)
        street_names = ["Main", "Oak", "Market", "Industrial", "Commerce", "Trade"]
        city = random.choice(CITIES)
        fields["address"] = f"{street_num} {random.choice(street_names)} St, {city}"
    
    # Registration number
    if random.random() * 100 < completeness_pct:
        fields["registration_number"] = f"REG-{random.randint(100000, 999999)}"
    
    return fields


# ============================================================================
# MAIN GENERATION LOGIC
# ============================================================================

def generate(
    batch_id: str,
    seed: int,
    count_per_profile: int = 100,
    distribution: Dict[str, float] = None
) -> Dict[str, Any]:
    """
    Generate synthetic KYCC data with realistic B2B supply chain patterns.
    
    Args:
        batch_id: Unique identifier for this batch
        seed: Random seed for reproducibility
        count_per_profile: Parties to generate per risk profile
        distribution: Optional custom distribution (e.g., {"excellent": 0.15, "good": 0.35, ...})
    
    Returns:
        Dict containing parties, accounts, transactions, relationships
    """
    random.seed(seed)
    
    # Use default distribution if not provided
    if distribution is None:
        distribution = {
            "excellent": 0.15,
            "good": 0.35,
            "fair": 0.35,
            "poor": 0.15
        }
    
    parties = []
    accounts = []
    transactions = []
    relationships = []
    
    # Calculate counts per profile
    profile_counts = {
        profile: int(count_per_profile * proportion)
        for profile, proportion in distribution.items()
    }
    
    # Pre-create party IDs for cross-linking
    party_id_to_profile: Dict[str, str] = {}
    party_id_to_type: Dict[str, str] = {}
    
    party_counter = 1
    
    # ========================================================================
    # STEP 1: Generate Parties & Accounts
    # ========================================================================
    
    for profile_name, count in profile_counts.items():
        cfg = PROFILE_CONFIGS[profile_name]
        
        for i in range(count):
            party_id = f"P-{seed}-{party_counter:05d}"
            party_counter += 1
            
            # Determine party type
            party_type = _weighted_choice(cfg.party_type_weights)
            party_id_to_profile[party_id] = profile_name
            party_id_to_type[party_id] = party_type
            
            # Company age
            company_age = random.uniform(*cfg.company_age_years_range)
            created_at = datetime.utcnow() - timedelta(days=int(company_age * 365.25))
            
            # Contact completeness
            completeness = random.uniform(*cfg.contact_completeness_range)
            contact_info = _generate_contact_info(completeness, party_id)
            
            # Build party
            party = {
                "party_id": party_id,
                "name": generate_company_name(party_type, profile_name),
                "profile": profile_name,  # Metadata for validation
                "party_type": party_type,
                "kyc_verified": 1 if random.random() < cfg.kyc_verified_prob else 0,
                "tax_id": f"TAX-{random.randint(100000, 999999)}" if random.random() < cfg.has_tax_id_prob else None,
                "created_at": created_at.isoformat() + "Z",
                "batch_id": batch_id,
                **contact_info  # Spread contact fields
            }
            parties.append(party)
            
            # Generate account(s) - most parties have 1 checking account
            account_type = _weighted_choice(cfg.account_type_weights)
            balance = round(random.uniform(*cfg.balance_range), 2)
            
            accounts.append({
                "account_id": f"ACC-{party_id}",
                "party_id": party_id,
                "account_type": account_type,
                "currency": "NRS",
                "balance": balance,
                "batch_id": batch_id,
            })
    
    # ========================================================================
    # STEP 2: Generate Relationships (Supply Chain Topology)
    # ========================================================================
    
    # Organize parties by type for supply chain logic
    parties_by_type: Dict[str, List[str]] = {}
    for pid, ptype in party_id_to_type.items():
        if ptype not in parties_by_type:
            parties_by_type[ptype] = []
        parties_by_type[ptype].append(pid)
    
    # Create realistic supply chain edges
    # Supplier → Manufacturer → Distributor → Retailer → Customer
    
    relationship_id_counter = 1
    
    def create_relationships(from_type: str, to_type: str, rel_type: str):
        """Create relationships between party types"""
        nonlocal relationship_id_counter
        
        if from_type not in parties_by_type or to_type not in parties_by_type:
            return
        
        from_parties = parties_by_type[from_type]
        to_parties = parties_by_type[to_type]
        
        for to_party_id in to_parties:
            profile = party_id_to_profile[to_party_id]
            cfg = PROFILE_CONFIGS[profile]
            
            # Determine how many upstream connections this party needs
            min_suppliers, max_suppliers = cfg.supplier_count_range
            num_suppliers = random.randint(min_suppliers, max_suppliers)
            
            # Select random suppliers
            if len(from_parties) > 0:
                suppliers = random.sample(
                    from_parties,
                    min(num_suppliers, len(from_parties))
                )
                
                for supplier_id in suppliers:
                    relationships.append({
                        "relationship_id": f"REL-{relationship_id_counter:06d}",
                        "from_party_id": supplier_id,
                        "to_party_id": to_party_id,
                        "relationship_type": rel_type,
                        "established_date": _rand_date(365),
                        "batch_id": batch_id,
                    })
                    relationship_id_counter += 1
    
    # Build supply chain topology
    create_relationships("supplier", "manufacturer", "supplies_to")
    create_relationships("manufacturer", "distributor", "manufactures_for")
    create_relationships("distributor", "retailer", "distributes_for")
    create_relationships("retailer", "customer", "sells_to")
    
    # Some cross-connections for realism
    create_relationships("supplier", "distributor", "supplies_to")
    create_relationships("manufacturer", "retailer", "manufactures_for")
    
    # ========================================================================
    # STEP 3: Generate Transactions
    # ========================================================================
    
    txn_id_counter = 1
    
    for party in parties:
        party_id = party["party_id"]
        profile = party["profile"]
        cfg = PROFILE_CONFIGS[profile]
        
        # Determine transaction count
        txn_count = random.randint(*cfg.txn_count_6m_range)
        
        # Determine if party has recent activity
        has_recent = random.random() < cfg.recent_activity_prob
        
        # Generate transactions
        for _ in range(txn_count):
            # Date distribution
            if has_recent:
                # More recent transactions
                days_back = random.choices(
                    [30, 90, 180],
                    weights=[0.5, 0.3, 0.2]
                )[0]
            else:
                # Older transactions
                days_back = random.randint(60, 180)
            
            txn_date = _rand_date(days_back)
            
            # Transaction type with proper distribution
            if random.random() < cfg.negative_amount_prob:
                txn_type = "credit_note"
                is_credit_note = True
            else:
                txn_type = random.choices(
                    ["invoice", "payment"],
                    weights=[0.6, 0.4]
                )[0]
                is_credit_note = False
            
            amount = _generate_transaction_amount(cfg, is_credit_note)
            
            # Get counterparty from relationships
            counterparty_id = None
            related_parties = [
                r["from_party_id"] if r["to_party_id"] == party_id else r["to_party_id"]
                for r in relationships
                if r["from_party_id"] == party_id or r["to_party_id"] == party_id
            ]
            
            if related_parties:
                counterparty_id = random.choice(related_parties)
            else:
                # Fallback: random party
                counterparty_id = random.choice([p["party_id"] for p in parties if p["party_id"] != party_id])
            
            transactions.append({
                "txn_id": f"TXN-{txn_id_counter:08d}",
                "party_id": party_id,
                "counterparty_id": counterparty_id,
                "account_id": f"ACC-{party_id}",
                "amount": amount,
                "currency": "NRS",
                "txn_type": txn_type,
                "ts": txn_date,
                "reference": f"Synthetic batch {batch_id}",
                "batch_id": batch_id,
            })
            txn_id_counter += 1
    
    # ========================================================================
    # RETURN PAYLOAD
    # ========================================================================
    
    payload = {
        "batch_id": batch_id,
        "seed": seed,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "distribution": distribution,
        "counts": {
            "parties": len(parties),
            "accounts": len(accounts),
            "transactions": len(transactions),
            "relationships": len(relationships),
        },
        "profile_breakdown": {
            profile: sum(1 for p in parties if p["profile"] == profile)
            for profile in RISK_PROFILES
        },
        "parties": parties,
        "accounts": accounts,
        "transactions": transactions,
        "relationships": relationships,
    }
    
    return payload


# ============================================================================
# CLI INTERFACE
# ============================================================================

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate synthetic KYCC profiles with realistic B2B patterns"
    )
    parser.add_argument(
        "--batch-id",
        required=True,
        help="Unique batch ID for this generation run"
    )
    parser.add_argument(
        "--out",
        default="backend/data/synthetic_profiles.json",
        help="Output JSON file path"
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducibility"
    )
    parser.add_argument(
        "--count",
        type=int,
        default=100,
        help="Total number of parties to generate"
    )
    parser.add_argument(
        "--scenario",
        choices=["balanced", "risky", "safe"],
        default="balanced",
        help="Risk distribution scenario"
    )
    
    args = parser.parse_args()
    
    # Define scenarios
    scenarios = {
        "balanced": {"excellent": 0.15, "good": 0.35, "fair": 0.35, "poor": 0.15},
        "risky": {"excellent": 0.05, "good": 0.20, "fair": 0.40, "poor": 0.35},
        "safe": {"excellent": 0.30, "good": 0.45, "fair": 0.20, "poor": 0.05},
    }
    
    distribution = scenarios[args.scenario]
    
    print("=" * 70)
    print("🏭 GENERATING SYNTHETIC KYCC DATA")
    print("=" * 70)
    print(f"Batch ID: {args.batch_id}")
    print(f"Seed: {args.seed}")
    print(f"Total parties: {args.count}")
    print(f"Scenario: {args.scenario}")
    print(f"Distribution: {distribution}")
    print()
    
    payload = generate(
        batch_id=args.batch_id,
        seed=args.seed,
        count_per_profile=args.count,
        distribution=distribution
    )
    
    # Write to file
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2))
    
    print("✅ Generation Complete!")
    print(f"   Written to: {out_path}")
    print(f"   Parties: {payload['counts']['parties']}")
    print(f"   Accounts: {payload['counts']['accounts']}")
    print(f"   Transactions: {payload['counts']['transactions']}")
    print(f"   Relationships: {payload['counts']['relationships']}")
    print()
    print("Profile Breakdown:")
    for profile, count in payload['profile_breakdown'].items():
        print(f"   {profile:10s}: {count:4d} ({count/payload['counts']['parties']*100:5.1f}%)")


if __name__ == "__main__":
    main()