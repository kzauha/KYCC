"""Generate labeled synthetic profiles for ML training data.

This module creates synthetic profiles with ground truth labels for credit risk
classification. Profiles are distributed across three risk levels (high/medium/low)
with exaggerated characteristics to reflect their risk classification.

Distribution: 30% high-risk, 40% medium-risk, 30% low-risk

Usage:
    python -m backend.scripts.generate_labeled_profiles \
        --batch-id LABELED_TRAIN_001 \
        --count 1000 \
        --out data/labeled_profiles.json
"""

import argparse
import json
import random
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any


@dataclass
class LabeledProfile:
    """Labeled synthetic profile for training."""
    party_name: str
    party_type: str
    kyc_score: float
    company_age_days: int
    transaction_count: int
    avg_transaction_amount: float
    balance_total: float
    account_type: str
    ground_truth: Dict[str, Any]


class DefaultProfileGenerator:
    """Generate synthetic profiles with known default risk levels."""

    def __init__(self, random_seed: int = 42):
        """Initialize with optional random seed for reproducibility."""
        self.random_seed = random_seed
        random.seed(random_seed)

    def generate_high_risk_profile(self, party_id: int) -> LabeledProfile:
        """Generate a high-risk profile (will_default=1).
        
        Characteristics:
        - Low KYC score (<30)
        - Very new company (<30 days)
        - Minimal transactions (1-5)
        - Low balance
        """
        return LabeledProfile(
            party_name=f"HighRisk Corp {party_id}",
            party_type=random.choice(["supplier", "manufacturer", "distributor"]),
            kyc_score=round(random.uniform(5, 28), 1),
            company_age_days=random.randint(1, 29),
            transaction_count=random.randint(1, 5),
            avg_transaction_amount=round(random.uniform(50, 200), 2),
            balance_total=round(random.uniform(100, 500), 2),
            account_type=random.choice(["checking"]),
            ground_truth={
                "will_default": 1,
                "risk_level": "high",
                "reason": "Low KYC score + New company + Minimal transactions"
            }
        )

    def generate_medium_risk_profile(self, party_id: int) -> LabeledProfile:
        """Generate a medium-risk profile (will_default=0.5).
        
        Characteristics:
        - Moderate KYC score (50-70)
        - Medium company age (100-365 days)
        - Some transactions (20-100)
        - Moderate balance
        """
        return LabeledProfile(
            party_name=f"MediumRisk LLC {party_id}",
            party_type=random.choice(["supplier", "manufacturer", "distributor", "retailer"]),
            kyc_score=round(random.uniform(50, 70), 1),
            company_age_days=random.randint(100, 365),
            transaction_count=random.randint(20, 100),
            avg_transaction_amount=round(random.uniform(500, 2000), 2),
            balance_total=round(random.uniform(5000, 25000), 2),
            account_type=random.choice(["checking", "savings"]),
            ground_truth={
                "will_default": 0.5,
                "risk_level": "medium",
                "reason": "Moderate KYC score + Medium company age + Moderate transaction activity"
            }
        )

    def generate_low_risk_profile(self, party_id: int) -> LabeledProfile:
        """Generate a low-risk profile (will_default=0).
        
        Characteristics:
        - High KYC score (>80)
        - Established company (>2 years)
        - Many transactions (200+)
        - High balance
        """
        return LabeledProfile(
            party_name=f"LowRisk Inc {party_id}",
            party_type=random.choice(["supplier", "manufacturer", "distributor", "retailer", "customer"]),
            kyc_score=round(random.uniform(80, 100), 1),
            company_age_days=random.randint(730, 3650),  # 2-10 years
            transaction_count=random.randint(200, 1000),
            avg_transaction_amount=round(random.uniform(2000, 10000), 2),
            balance_total=round(random.uniform(50000, 500000), 2),
            account_type=random.choice(["checking", "savings", "money_market"]),
            ground_truth={
                "will_default": 0,
                "risk_level": "low",
                "reason": "High KYC score + Established company + Extensive transaction history"
            }
        )


class RiskScenarioBuilder:
    """Exaggerate profile characteristics for risk levels."""

    def __init__(self, generator: DefaultProfileGenerator):
        """Initialize with a profile generator."""
        self.generator = generator

    def build_scenario(self, risk_level: str, count: int) -> List[LabeledProfile]:
        """Build profiles for a specific risk level.
        
        Args:
            risk_level: One of 'high', 'medium', 'low'
            count: Number of profiles to generate
            
        Returns:
            List of LabeledProfile objects
        """
        profiles = []
        for i in range(count):
            if risk_level == "high":
                profile = self.generator.generate_high_risk_profile(i)
            elif risk_level == "medium":
                profile = self.generator.generate_medium_risk_profile(i)
            elif risk_level == "low":
                profile = self.generator.generate_low_risk_profile(i)
            else:
                raise ValueError(f"Unknown risk level: {risk_level}")
            
            profiles.append(profile)
        return profiles

    def apply_risk_characteristics(self, profile: LabeledProfile, risk_level: str) -> LabeledProfile:
        """Apply exaggerated characteristics to a profile based on risk level.
        
        This method can be used to transform an existing profile.
        """
        if risk_level == "high":
            profile.kyc_score = min(profile.kyc_score, 28)
            profile.company_age_days = min(profile.company_age_days, 29)
            profile.transaction_count = min(profile.transaction_count, 5)
            profile.balance_total = min(profile.balance_total, 500)
        elif risk_level == "medium":
            profile.kyc_score = max(50, min(profile.kyc_score, 70))
            profile.company_age_days = max(100, min(profile.company_age_days, 365))
            profile.transaction_count = max(20, min(profile.transaction_count, 100))
            profile.balance_total = max(5000, min(profile.balance_total, 25000))
        elif risk_level == "low":
            profile.kyc_score = max(80, profile.kyc_score)
            profile.company_age_days = max(730, profile.company_age_days)
            profile.transaction_count = max(200, profile.transaction_count)
            profile.balance_total = max(50000, profile.balance_total)
        
        return profile


class LabeledDatasetExporter:
    """Export labeled profiles with ground truth metadata."""

    def export_to_json(self, profiles: List[LabeledProfile], filepath: str) -> None:
        """Export profiles to JSON file.
        
        Args:
            profiles: List of LabeledProfile objects
            filepath: Output file path
        """
        profiles_dict = [asdict(p) for p in profiles]
        
        dataset = {
            "batch_id": "LABELED_TRAIN_001",
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "profile_count": len(profiles),
            "profiles": profiles_dict
        }
        
        with open(filepath, "w") as f:
            json.dump(dataset, f, indent=2)

    def export_with_metadata(self, profiles: List[LabeledProfile], filepath: str) -> None:
        """Export profiles with additional metadata.
        
        Args:
            profiles: List of LabeledProfile objects
            filepath: Output file path
        """
        profiles_dict = [asdict(p) for p in profiles]
        
        # Calculate distribution statistics
        risk_distribution = {
            "high": len([p for p in profiles if p.ground_truth["will_default"] == 1]),
            "medium": len([p for p in profiles if p.ground_truth["will_default"] == 0.5]),
            "low": len([p for p in profiles if p.ground_truth["will_default"] == 0])
        }
        
        dataset = {
            "batch_id": "LABELED_TRAIN_001",
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "profile_count": len(profiles),
            "distribution": risk_distribution,
            "profiles": profiles_dict
        }
        
        with open(filepath, "w") as f:
            json.dump(dataset, f, indent=2)


def main():
    """Generate labeled profiles dataset."""
    parser = argparse.ArgumentParser(description="Generate labeled synthetic profiles")
    parser.add_argument("--batch-id", default="LABELED_TRAIN_001", help="Batch ID")
    parser.add_argument("--count", type=int, default=1000, help="Total profiles to generate")
    parser.add_argument("--out", default="backend/data/labeled_profiles.json", help="Output file")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")
    
    args = parser.parse_args()
    
    # Initialize generator
    generator = DefaultProfileGenerator(random_seed=args.seed)
    builder = RiskScenarioBuilder(generator)
    exporter = LabeledDatasetExporter()
    
    # Calculate distribution: 30% high, 40% medium, 30% low
    high_count = int(args.count * 0.30)
    medium_count = int(args.count * 0.40)
    low_count = args.count - high_count - medium_count
    
    print(f"Generating {args.count} labeled profiles...")
    print(f"  - High-risk: {high_count} (30%)")
    print(f"  - Medium-risk: {medium_count} (40%)")
    print(f"  - Low-risk: {low_count} (30%)")
    
    # Generate profiles
    all_profiles = []
    
    # Generate high-risk profiles
    all_profiles.extend(builder.build_scenario("high", high_count))
    
    # Generate medium-risk profiles
    all_profiles.extend(builder.build_scenario("medium", medium_count))
    
    # Generate low-risk profiles
    all_profiles.extend(builder.build_scenario("low", low_count))
    
    # Shuffle profiles
    random.shuffle(all_profiles)
    
    # Create output directory if needed
    output_path = Path(args.out)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Export with metadata
    exporter.export_with_metadata(all_profiles, args.out)
    
    print(f"\nDataset exported to: {args.out}")
    print(f"Total profiles: {len(all_profiles)}")
    
    # Print summary
    risk_summary = {
        "high": len([p for p in all_profiles if p.ground_truth["will_default"] == 1]),
        "medium": len([p for p in all_profiles if p.ground_truth["will_default"] == 0.5]),
        "low": len([p for p in all_profiles if p.ground_truth["will_default"] == 0])
    }
    print(f"Distribution: {risk_summary}")


if __name__ == "__main__":
    main()
