"""Mappings and defaults for synthetic seed ingestion.

Aligns synthetic data with canonical KYCC backend enums and schema.
All mappings are validated against actual backend models.
"""
from dataclasses import dataclass
from typing import Dict, Optional

# ============================================================================
# PARTY TYPE MAPPINGS
# ============================================================================
# Backend PartyType enum values (from app.models.models)
CANONICAL_PARTY_TYPES = [
    "supplier",
    "manufacturer", 
    "distributor",
    "retailer",
    "customer"
]

# Synthetic → Canonical party type mapping
PARTY_TYPE_MAP: Dict[str, str] = {
    # Direct mappings (synthetic matches canonical)
    "supplier": "supplier",
    "manufacturer": "manufacturer",
    "distributor": "distributor",
    "retailer": "retailer",
    "customer": "customer",
    
    # Legacy/alternative names
    "individual": "customer",  # Map individuals to customers
    "business": "supplier",    # Generic business → supplier
    "vendor": "supplier",
    "wholesaler": "distributor",
    "merchant": "retailer",
}

# Default party type per risk profile (if needed)
PROFILE_PARTY_TYPE_DEFAULT: Dict[str, str] = {
    "excellent": "manufacturer",  # Most stable
    "good": "supplier",
    "fair": "retailer",
    "poor": "customer",
}


# ============================================================================
# TRANSACTION TYPE MAPPINGS
# ============================================================================
# Backend TransactionType enum values (from app.models.models)
CANONICAL_TRANSACTION_TYPES = [
    "invoice",
    "payment",
    "credit_note"
]

# Synthetic → Canonical transaction type mapping
TRANSACTION_TYPE_MAP: Dict[str, str] = {
    # Direct mappings
    "invoice": "invoice",
    "payment": "payment",
    "credit_note": "credit_note",
    
    # Common alternatives/synonyms
    "deposit": "payment",
    "withdrawal": "payment",
    "transfer": "payment",
    "wire": "payment",
    "ach": "payment",
    "check": "payment",
    
    # Invoice-related
    "bill": "invoice",
    "purchase_order": "invoice",
    "sales_order": "invoice",
    
    # Credit-related
    "refund": "credit_note",
    "reversal": "credit_note",
    "chargeback": "credit_note",
    "adjustment": "credit_note",
}


# ============================================================================
# RELATIONSHIP TYPE MAPPINGS
# ============================================================================
# Backend RelationshipType enum values (from app.models.models)
CANONICAL_RELATIONSHIP_TYPES = [
    "supplies_to",
    "manufactures_for",
    "distributes_for",
    "sells_to"
]

# Synthetic → Canonical relationship type mapping
RELATIONSHIP_TYPE_MAP: Dict[str, str] = {
    # Direct mappings
    "supplies_to": "supplies_to",
    "manufactures_for": "manufactures_for",
    "distributes_for": "distributes_for",
    "sells_to": "sells_to",
    
    # Common alternatives/synonyms
    "trades_with": "sells_to",        # Generic trading
    "partners_with": "sells_to",      # Business partnership
    "owns": "sells_to",               # Ownership relationship
    "subsidiary_of": "supplies_to",   # Corporate structure
    
    # Supply chain specific
    "sources_from": "supplies_to",
    "procures_from": "supplies_to",
    "purchases_from": "supplies_to",
    
    # Distribution specific
    "wholesales_to": "distributes_for",
    "retails_to": "sells_to",
    
    # Manufacturing specific
    "produces_for": "manufactures_for",
    "assembles_for": "manufactures_for",
}


# ============================================================================
# ACCOUNT TYPE MAPPINGS
# ============================================================================
# Common account types (extend as needed)
ACCOUNT_TYPE_MAP: Dict[str, str] = {
    "checking": "checking",
    "savings": "savings",
    "business": "checking",
    "operating": "checking",
    "revenue": "checking",
}


# ============================================================================
# VALIDATION HELPERS
# ============================================================================

def validate_party_type(party_type: str) -> str:
    """
    Validate and map party type to canonical value.
    
    Raises:
        ValueError: If party_type cannot be mapped
    """
    mapped = PARTY_TYPE_MAP.get(party_type)
    if mapped is None:
        raise ValueError(
            f"Invalid party_type '{party_type}'. "
            f"Must be one of {list(PARTY_TYPE_MAP.keys())}"
        )
    return mapped


def validate_transaction_type(txn_type: str) -> str:
    """
    Validate and map transaction type to canonical value.
    
    Raises:
        ValueError: If txn_type cannot be mapped
    """
    mapped = TRANSACTION_TYPE_MAP.get(txn_type)
    if mapped is None:
        raise ValueError(
            f"Invalid transaction type '{txn_type}'. "
            f"Must be one of {list(TRANSACTION_TYPE_MAP.keys())}"
        )
    return mapped


def validate_relationship_type(rel_type: str) -> str:
    """
    Validate and map relationship type to canonical value.
    
    Raises:
        ValueError: If rel_type cannot be mapped
    """
    mapped = RELATIONSHIP_TYPE_MAP.get(rel_type)
    if mapped is None:
        raise ValueError(
            f"Invalid relationship type '{rel_type}'. "
            f"Must be one of {list(RELATIONSHIP_TYPE_MAP.keys())}"
        )
    return mapped


# ============================================================================
# CONFIGURATION DATACLASS
# ============================================================================

@dataclass
class MappingConfig:
    """
    Central configuration for all synthetic data mappings.
    
    Use this to ensure consistent mapping across all ingestion pipelines.
    """
    
    # Type mappings
    party_type_map: Dict[str, str]
    transaction_type_map: Dict[str, str]
    relationship_type_map: Dict[str, str]
    account_type_map: Dict[str, str]
    
    # Profile defaults
    profile_party_type_default: Dict[str, str]
    
    # Canonical values (for validation)
    canonical_party_types: list[str]
    canonical_transaction_types: list[str]
    canonical_relationship_types: list[str]
    
    def validate_party_type(self, party_type: str) -> str:
        """Map and validate party type"""
        return validate_party_type(party_type)
    
    def validate_transaction_type(self, txn_type: str) -> str:
        """Map and validate transaction type"""
        return validate_transaction_type(txn_type)
    
    def validate_relationship_type(self, rel_type: str) -> str:
        """Map and validate relationship type"""
        return validate_relationship_type(rel_type)


def get_default_mapping() -> MappingConfig:
    """
    Get default mapping configuration.
    
    Returns:
        MappingConfig with all mappings initialized
    """
    return MappingConfig(
        party_type_map=PARTY_TYPE_MAP,
        transaction_type_map=TRANSACTION_TYPE_MAP,
        relationship_type_map=RELATIONSHIP_TYPE_MAP,
        account_type_map=ACCOUNT_TYPE_MAP,
        profile_party_type_default=PROFILE_PARTY_TYPE_DEFAULT,
        canonical_party_types=CANONICAL_PARTY_TYPES,
        canonical_transaction_types=CANONICAL_TRANSACTION_TYPES,
        canonical_relationship_types=CANONICAL_RELATIONSHIP_TYPES,
    )


# ============================================================================
# INGESTION ADAPTER
# ============================================================================

class SyntheticDataAdapter:
    """
    Adapter to transform synthetic data into canonical KYCC format.
    
    Usage:
        adapter = SyntheticDataAdapter()
        canonical_party = adapter.adapt_party(synthetic_party)
    """
    
    def __init__(self, config: Optional[MappingConfig] = None):
        self.config = config or get_default_mapping()
    
    def adapt_party(self, party: dict) -> dict:
        """
        Transform synthetic party to canonical format.
        
        Args:
            party: Synthetic party dict
            
        Returns:
            Canonical party dict ready for DB insertion
        """
        return {
            "name": party["name"],
            "party_type": self.config.validate_party_type(party["party_type"]),
            "kyc_verified": party.get("kyc_verified", 0),
            "tax_id": party.get("tax_id"),
            "registration_number": party.get("registration_number"),
            "address": party.get("address"),
            "contact_person": party.get("contact_person"),
            "email": party.get("email"),
            "phone": party.get("phone"),
        }
    
    def adapt_transaction(self, txn: dict) -> dict:
        """
        Transform synthetic transaction to canonical format.
        
        Args:
            txn: Synthetic transaction dict
            
        Returns:
            Canonical transaction dict ready for DB insertion
        """
        # Parse ISO timestamp to datetime
        from datetime import datetime
        ts_str = txn["ts"].replace("Z", "+00:00")
        transaction_date = datetime.fromisoformat(ts_str)
        
        return {
            "party_id": None,  # Will be set by ingestion logic
            "counterparty_id": None,  # Will be set by ingestion logic
            "transaction_date": transaction_date,
            "amount": txn["amount"],
            "transaction_type": self.config.validate_transaction_type(txn["txn_type"]),
            "reference": txn.get("reference", "Synthetic"),
        }
    
    def adapt_relationship(self, rel: dict) -> dict:
        """
        Transform synthetic relationship to canonical format.
        
        Args:
            rel: Synthetic relationship dict
            
        Returns:
            Canonical relationship dict ready for DB insertion
        """
        # Parse ISO timestamp to datetime
        from datetime import datetime
        date_str = rel["established_date"].replace("Z", "+00:00")
        established_date = datetime.fromisoformat(date_str)
        
        return {
            "from_party_id": None,  # Will be set by ingestion logic
            "to_party_id": None,  # Will be set by ingestion logic
            "relationship_type": self.config.validate_relationship_type(rel["relationship_type"]),
            "established_date": established_date,
        }


# ============================================================================
# TESTING & VALIDATION
# ============================================================================

def test_mappings():
    """Validate all mappings are correct"""
    
    print("Testing mappings...")
    
    # Test party types
    for synthetic, expected in PARTY_TYPE_MAP.items():
        assert expected in CANONICAL_PARTY_TYPES, f"Invalid mapping: {synthetic} → {expected}"
    print("✅ Party type mappings valid")
    
    # Test transaction types
    for synthetic, expected in TRANSACTION_TYPE_MAP.items():
        assert expected in CANONICAL_TRANSACTION_TYPES, f"Invalid mapping: {synthetic} → {expected}"
    print("✅ Transaction type mappings valid")
    
    # Test relationship types
    for synthetic, expected in RELATIONSHIP_TYPE_MAP.items():
        assert expected in CANONICAL_RELATIONSHIP_TYPES, f"Invalid mapping: {synthetic} → {expected}"
    print("✅ Relationship type mappings valid")
    
    # Test adapter
    adapter = SyntheticDataAdapter()
    
    test_party = {
        "name": "Test Corp",
        "party_type": "manufacturer",
        "kyc_verified": 1,
        "tax_id": "TAX-123456"
    }
    adapted = adapter.adapt_party(test_party)
    assert adapted["party_type"] == "manufacturer"
    print("✅ Adapter works correctly")
    
    print("\n🎉 All mappings validated!")


if __name__ == "__main__":
    test_mappings()