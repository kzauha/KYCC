"""Generate synthetic profiles and labels for Iterative Learning Pipeline.

Outputs TWO files per batch:
1. data/{BATCH_ID}_profiles.json: Customer features (NO LABELS)
2. data/{BATCH_ID}_labels.json: Ground truth labels (NO FEATURES)

Usage:
    python scripts/generate_synthetic_batch.py --batch-number 1 --count 100
"""
from __future__ import annotations

import argparse
import json
import random
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Tuple

# Import shared logic from seed script (copying key parts to ensure standalone execution)
# Ideally we would refactor to shared module, but for this task we duplicate needed configs.

RISK_PROFILES = ["excellent", "good", "fair", "poor"]

@dataclass
class ProfileConfig:
    name: str
    kyc_verified_prob: float
    has_tax_id_prob: float
    default_prob: float  # NEW: Probability of default
    # ... (other fields simplified for brevity or reused)

# Simplified config for this specific task
PROFILE_DEFAULTS = {
    "excellent": 0.01,
    "good": 0.05,
    "fair": 0.20,
    "poor": 0.60
}

# Re-using the robust generation logic from seed_synthetic_profiles would be best.
# To avoid massive code duplication in this response, I will import from seed_synthetic_profiles
# if possible, or assume I can write a wrapper.
# However, seed_synthetic_profiles uses 'batch_id' string.
# I will Modify the original script content I read to support the new requirements
# and write it to the new file.

# ... [Copying relevant parts from seed_synthetic_profiles.py and modifying] ...

import sys
import os
# Ensure current dir is in path for direct import
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

# Add backend to path for app imports if needed
sys.path.append(os.path.join(current_dir, '..'))

try:
    # Try direct import (when running as script)
    from seed_synthetic_profiles import (
        PROFILE_CONFIGS, generate_company_name, _rand_date, _weighted_choice,
        _generate_contact_info, _generate_transaction_amount
    )
    from seed_synthetic_profiles import generate as generate_seed
except ImportError:
    try:
        # Try module import (when running from backend)
        from scripts.seed_synthetic_profiles import (
            PROFILE_CONFIGS, generate_company_name, _rand_date, _weighted_choice,
            _generate_contact_info, _generate_transaction_amount
        )
        from scripts.seed_synthetic_profiles import generate as generate_seed
    except ImportError:
        # Try backend module import
        from backend.scripts.seed_synthetic_profiles import (
            PROFILE_CONFIGS, generate_company_name, _rand_date, _weighted_choice,
            _generate_contact_info, _generate_transaction_amount
        )
        from backend.scripts.seed_synthetic_profiles import generate as generate_seed

# We need the full logic to ensure compatible data structure.
# I will copy the structure of seed_synthetic_profiles.py roughly but add the splitting logic.

def generate_batch_data(batch_id: str, count: int, seed: int = 42):
    """Generate batch data using the FULL batch_id string."""
    random.seed(seed)
    
    # Borrowing generation logic from seed_synthetic_profiles.py (conceptually)
    # Since I cannot easily import it (it's in scripts module), I will shell out to it 
    # OR replicate the essential parts.
    # The prompt explicitly asks to "Update the script... Accept batch number... Generate TWO files".
    # I will create a script that USES `seed_synthetic_profiles` as a library if possible,
    # or just implements the splitting wrapper around it.
    
    # Let's try to import the generate function.
    try:
        from scripts.seed_synthetic_profiles import generate
    except ImportError:
        # If running from backend root
        from backend.scripts.seed_synthetic_profiles import generate

    # Helper to add wil_default
    def add_labels(payload: Dict):
        parties = payload["parties"]
        labels = []
        for p in parties:
            profile = p.get("profile", "fair")
            prob = PROFILE_DEFAULTS.get(profile, 0.1)
            
            # Deterministic label based on seed/party_id to allow reproduction
            # But we want random noise too.
            p_seed = hash(p["party_id"])
            rng = random.Random(p_seed + seed)
            will_default = 1 if rng.random() < prob else 0
            
            p["will_default"] = will_default
            
        return payload

    # 1. Generate full payload
    payload = generate_seed(
        batch_id=batch_id,
        seed=seed,
        count_per_profile=count
    )
    
    # 2. Add Labels
    payload_with_labels = add_labels(payload)
    
    # 3. Split
    # Profiles: Remove 'will_default'
    profiles_clean = []
    labels_only = []
    
    for p in payload_with_labels["parties"]:
        # Extract Label
        labels_only.append({
            "party_id": p["party_id"],
            "will_default": p["will_default"],
            "batch_id": batch_id
        })
        
        # Clean Profile
        p_clean = p.copy()
        if "will_default" in p_clean:
            del p_clean["will_default"]
        # Also remove 'profile' name if that hints at label?
        # User prompt doesn't strictly say remove 'profile', but 'profile' (poor/good) correlates 100% with risk config.
        # Ideally we keep 'profile' as a feature (maybe externally derived rating?) or remove it.
        # Valid KYC data usually doesn't have "poor/good" label.
        # I will remove 'profile' from the cleaned data to prevent leakage.
        if "profile" in p_clean:
            del p_clean["profile"]
            
        profiles_clean.append(p_clean)
        
    # Reconstruct payload for profiles file
    profiles_payload = payload.copy()
    profiles_payload["parties"] = profiles_clean
    # Transactions, etc remain
    
    # Structure labels file correctly
    labels_payload = {
        "batch_id": batch_id,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "profiles": labels_only
    }
    
    # 4. Save
    base_dir = Path("data")
    base_dir.mkdir(exist_ok=True)
    
    prof_path = base_dir / f"{batch_id}_profiles.json"
    lbl_path = base_dir / f"{batch_id}_labels.json"
    
    prof_path.write_text(json.dumps(profiles_payload, indent=2))
    lbl_path.write_text(json.dumps(labels_payload, indent=2))
    
    print(f"✓ Generated {batch_id}")
    print(f"  - Profiles: {prof_path}")
    print(f"  - Labels:   {lbl_path}")

def generate_new_batch(batch_id: str, count: int):
    """Entry point for external scripts. Accepts full batch_id string."""
    # Extract seed from batch_id for reproducibility
    seed = hash(batch_id) % 10000
    generate_batch_data(batch_id, count, seed=seed)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate synthetic batch files")
    parser.add_argument("--batch-number", type=int, required=True)
    parser.add_argument("--count", type=int, default=100)
    
    args = parser.parse_args()
    generate_new_batch(args.batch_number, args.count)
