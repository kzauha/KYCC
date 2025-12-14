"""Ingest labeled synthetic profiles into database.

This script loads labeled profiles from JSON and populates the parties and
ground_truth_labels tables. Validates schema before ingestion.

Usage:
    python -m backend.scripts.ingest_labeled_data \
        --input data/labeled_profiles.json \
        --batch-id LABELED_TRAIN_001
"""

import argparse
import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

# Add backend to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.database import SessionLocal
from app.db import crud
from app.models.models import Party


class LabeledDataIngester:
    """Ingest labeled synthetic profiles into database."""

    def __init__(self, db_session=None):
        """Initialize ingester with optional database session."""
        self.db = db_session or SessionLocal()
        self.validation_errors: List[str] = []

    def load_from_json(self, filepath: str) -> Dict[str, Any]:
        """Load profiles from JSON file.
        
        Args:
            filepath: Path to JSON file
            
        Returns:
            Dictionary with batch metadata and profiles list
            
        Raises:
            FileNotFoundError: If file doesn't exist
            json.JSONDecodeError: If file is not valid JSON
        """
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {filepath}")
        
        with open(path, 'r') as f:
            data = json.load(f)
        
        return data

    def validate_schema(self, data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate that data has expected structure.
        
        Args:
            data: Dictionary loaded from JSON
            
        Returns:
            (is_valid, errors_list)
        """
        errors = []
        
        # Check top-level keys
        if 'batch_id' not in data:
            errors.append("Missing 'batch_id' field")
        if 'profiles' not in data:
            errors.append("Missing 'profiles' field")
        
        if errors:
            return False, errors
        
        profiles = data.get('profiles', [])
        if not isinstance(profiles, list):
            return False, ["'profiles' must be a list"]
        
        if len(profiles) == 0:
            return False, ["'profiles' list is empty"]
        
        # Validate first profile as sample
        required_fields = [
            'party_name', 'party_type', 'kyc_score', 'company_age_days',
            'transaction_count', 'avg_transaction_amount', 'balance_total',
            'account_type', 'ground_truth'
        ]
        
        sample_profile = profiles[0]
        for field in required_fields:
            if field not in sample_profile:
                errors.append(f"Missing required field '{field}' in profile")
        
        # Validate ground_truth sub-fields
        if 'ground_truth' in sample_profile:
            gt = sample_profile['ground_truth']
            for gt_field in ['will_default', 'risk_level', 'reason']:
                if gt_field not in gt:
                    errors.append(f"Missing required field '{gt_field}' in ground_truth")
        
        return len(errors) == 0, errors

    def create_parties_in_db(self, profiles: List[Dict[str, Any]], batch_id: str) -> Tuple[int, List[str]]:
        """Create Party records from profiles.
        
        Args:
            profiles: List of profile dictionaries
            batch_id: Batch identifier for tracking
            
        Returns:
            (created_count, error_messages)
        """
        created_count = 0
        errors = []
        
        for idx, profile in enumerate(profiles):
            try:
                # Check if party already exists
                existing = crud.get_party_by_tax_id(
                    self.db,
                    tax_id=f"{batch_id}_{profile['party_name']}"
                )
                
                if existing:
                    continue
                
                # Create party
                party = crud.create_party(
                    self.db,
                    name=profile['party_name'],
                    party_type=profile['party_type'],
                    tax_id=f"{batch_id}_{profile['party_name']}",
                    batch_id=batch_id,
                    kyc_verified=1 if profile['kyc_score'] > 70 else 0
                )
                created_count += 1
                
            except Exception as e:
                errors.append(f"Error creating party {idx}: {str(e)}")
        
        return created_count, errors

    def store_ground_truth_labels(self, profiles: List[Dict[str, Any]], batch_id: str) -> Tuple[int, List[str]]:
        """Store ground truth labels for profiles.
        
        Args:
            profiles: List of profile dictionaries
            batch_id: Batch identifier
            
        Returns:
            (created_count, error_messages)
        """
        created_count = 0
        errors = []
        
        for idx, profile in enumerate(profiles):
            try:
                # Find party
                party = crud.get_party_by_tax_id(
                    self.db,
                    tax_id=f"{batch_id}_{profile['party_name']}"
                )
                
                if not party:
                    errors.append(f"Party not found for {profile['party_name']}")
                    continue
                
                gt = profile['ground_truth']
                
                # Create label
                label = crud.create_ground_truth_label(
                    self.db,
                    party_id=party.id,
                    will_default=gt['will_default'],
                    risk_level=gt['risk_level'],
                    label_source='synthetic',
                    reason=gt.get('reason', ''),
                    label_confidence=1.0,
                    dataset_batch=batch_id
                )
                created_count += 1
                
            except Exception as e:
                errors.append(f"Error storing label {idx}: {str(e)}")
        
        return created_count, errors

    def ingest(self, filepath: str, batch_id: Optional[str] = None) -> Dict[str, Any]:
        """Main ingestion pipeline: load, validate, create parties, store labels.
        
        Args:
            filepath: Path to JSON file
            batch_id: Optional override for batch_id (uses batch_id from JSON if not provided)
            
        Returns:
            Dictionary with ingestion results
        """
        # Load data
        try:
            data = self.load_from_json(filepath)
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to load JSON: {str(e)}',
                'parties_created': 0,
                'labels_created': 0
            }
        
        # Use provided batch_id or from JSON
        batch_id = batch_id or data.get('batch_id', 'DEFAULT_BATCH')
        
        # Validate schema
        is_valid, validation_errors = self.validate_schema(data)
        if not is_valid:
            return {
                'success': False,
                'error': 'Schema validation failed',
                'validation_errors': validation_errors,
                'parties_created': 0,
                'labels_created': 0
            }
        
        profiles = data['profiles']
        
        # Create parties
        parties_created, party_errors = self.create_parties_in_db(profiles, batch_id)
        
        # Store labels
        labels_created, label_errors = self.store_ground_truth_labels(profiles, batch_id)
        
        all_errors = party_errors + label_errors
        
        return {
            'success': len(all_errors) == 0,
            'batch_id': batch_id,
            'total_profiles': len(profiles),
            'parties_created': parties_created,
            'labels_created': labels_created,
            'errors': all_errors if all_errors else None,
            'timestamp': datetime.utcnow().isoformat()
        }


def main():
    """CLI entry point for ingestion."""
    parser = argparse.ArgumentParser(
        description='Ingest labeled synthetic profiles into database'
    )
    parser.add_argument(
        '--input',
        type=str,
        default='backend/data/labeled_profiles.json',
        help='Path to labeled profiles JSON file'
    )
    parser.add_argument(
        '--batch-id',
        type=str,
        default=None,
        help='Batch ID (uses value from JSON if not provided)'
    )
    
    args = parser.parse_args()
    
    print(f"Ingesting labeled profiles from {args.input}...")
    
    ingester = LabeledDataIngester()
    result = ingester.ingest(args.input, batch_id=args.batch_id)
    
    print(json.dumps(result, indent=2))
    
    if result['success']:
        print(f"\n✓ Ingestion complete!")
        print(f"  Parties created: {result['parties_created']}")
        print(f"  Labels created: {result['labels_created']}")
    else:
        print(f"\n✗ Ingestion failed!")
        if result.get('error'):
            print(f"  Error: {result['error']}")
        if result.get('validation_errors'):
            for err in result['validation_errors']:
                print(f"  - {err}")
        if result.get('errors'):
            for err in result['errors'][:5]:  # Show first 5
                print(f"  - {err}")


if __name__ == '__main__':
    main()
