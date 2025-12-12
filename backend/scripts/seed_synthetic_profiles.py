"""Generate synthetic profiles (good/normal/poor) and write to JSON.

- Generates 500 parties per profile (good/normal/poor)
- Ensures profile tags, batch_id, seed for determinism
- Emits parties, accounts (>=1 per party), inter-party transactions, and relationships

Usage:
    python -m backend.scripts.seed_synthetic_profiles --batch-id BATCH123 --out data/synthetic_profiles.json
"""
from __future__ import annotations

import argparse
import json
import random
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any

DEFAULT_COUNT_PER_PROFILE = 500
PROFILES = ["good", "normal", "poor"]


@dataclass
class ProfileConfig:
    name: str
    txn_count: int
    amount_range: tuple[float, float]
    negative_bias: float  # probability of negative amounts
    kyc_verified: int
    balance_range: tuple[float, float]


PROFILE_CONFIGS: Dict[str, ProfileConfig] = {
    "good": ProfileConfig(
        name="good",
        txn_count=12,
        amount_range=(200.0, 2000.0),
        negative_bias=0.2,
        kyc_verified=1,
        balance_range=(5000.0, 20000.0),
    ),
    "normal": ProfileConfig(
        name="normal",
        txn_count=10,
        amount_range=(100.0, 1200.0),
        negative_bias=0.35,
        kyc_verified=1,
        balance_range=(2000.0, 8000.0),
    ),
    "poor": ProfileConfig(
        name="poor",
        txn_count=8,
        amount_range=(50.0, 600.0),
        negative_bias=0.6,
        kyc_verified=0,
        balance_range=(200.0, 2000.0),
    ),
}

REL_TYPES = ["supplies_to", "manufactures_for", "distributes_for", "sells_to", "trades_with"]
TXN_TYPES = ["invoice", "payment", "credit_note", "deposit", "withdrawal"]


def _rand_amount(cfg: ProfileConfig) -> float:
    base = random.uniform(*cfg.amount_range)
    sign = -1.0 if random.random() < cfg.negative_bias else 1.0
    return round(sign * base, 2)


def _rand_date(days_back: int = 120) -> str:
    now = datetime.utcnow()
    dt = now - timedelta(days=random.randint(0, days_back))
    return dt.isoformat() + "Z"


def generate(batch_id: str, seed: int, count_per_profile: int = DEFAULT_COUNT_PER_PROFILE) -> Dict[str, Any]:
    random.seed(seed)
    parties = []
    accounts = []
    transactions = []
    relationships = []

    # Pre-create party ids for cross-links
    party_ids: List[str] = []
    for profile in PROFILES:
        prefix = profile[0].upper()
        for i in range(1, count_per_profile + 1):
            party_ids.append(f"{prefix}-{i:04d}")

    # Build parties and accounts
    idx = 0
    for profile in PROFILES:
        cfg = PROFILE_CONFIGS[profile]
        prefix = profile[0].upper()
        for i in range(1, count_per_profile + 1):
            idx += 1
            party_id = f"{prefix}-{i:04d}"
            name = f"{profile.title()} Party {i:04d}"
            parties.append({
                "party_id": party_id,
                "name": name,
                "profile": profile,
                "party_type": "individual" if profile in ("good", "normal") else "business",
                "kyc_verified": cfg.kyc_verified,
                "batch_id": batch_id,
            })
            acct_id = f"ACC-{party_id}"
            accounts.append({
                "account_id": acct_id,
                "party_id": party_id,
                "account_type": "checking",
                "currency": "USD",
                "balance": round(random.uniform(*cfg.balance_range), 2),
                "batch_id": batch_id,
            })

    # Build transactions and relationships
    for party in parties:
        cfg = PROFILE_CONFIGS[party["profile"]]
        party_id = party["party_id"]
        acct_id = f"ACC-{party_id}"
        for _ in range(cfg.txn_count):
            counterparty_id = random.choice([pid for pid in party_ids if pid != party_id])
            amount = _rand_amount(cfg)
            txn_type = random.choice(TXN_TYPES)
            transactions.append({
                "txn_id": f"T-{party_id}-{random.randint(1,999999):06d}",
                "party_id": party_id,
                "counterparty_id": counterparty_id,
                "account_id": acct_id,
                "amount": amount,
                "currency": "USD",
                "txn_type": txn_type,
                "ts": _rand_date(),
                "reference": "seeded synthetic",
                "batch_id": batch_id,
            })
            # Create a relationship edge per counterparty hit
            relationships.append({
                "from_party_id": party_id,
                "to_party_id": counterparty_id,
                "relationship_type": random.choice(REL_TYPES),
                "batch_id": batch_id,
                "established_date": _rand_date(365),
            })

    payload = {
        "batch_id": batch_id,
        "seed": seed,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "counts": {
            "parties": len(parties),
            "accounts": len(accounts),
            "transactions": len(transactions),
            "relationships": len(relationships),
        },
        "parties": parties,
        "accounts": accounts,
        "transactions": transactions,
        "relationships": relationships,
    }
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate synthetic profiles and write to JSON")
    parser.add_argument("--batch-id", required=True, help="Unique batch id for this seed run")
    parser.add_argument("--out", default="backend/data/synthetic_profiles.json", help="Output JSON path")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for determinism")
    parser.add_argument("--count", type=int, default=DEFAULT_COUNT_PER_PROFILE, help="Count per profile (good/normal/poor)")
    args = parser.parse_args()

    payload = generate(batch_id=args.batch_id, seed=args.seed, count_per_profile=args.count)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2))
    print(f"Wrote synthetic seed to {out_path} with batch {args.batch_id}")


if __name__ == "__main__":
    main()
