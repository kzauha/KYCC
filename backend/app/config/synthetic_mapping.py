"""Mappings and defaults for synthetic seed ingestion.

Mapping is config-driven so adapters can convert synthetic values to canonical enums
without code edits. Extend as needed.
"""
from dataclasses import dataclass
from typing import Dict

# Profile defaults
PROFILE_PARTY_TYPE_DEFAULT = {
    "good": "individual",
    "normal": "individual",
    "poor": "business",
}

# Synthetic -> canonical transaction type
TRANSACTION_TYPE_MAP: Dict[str, str] = {
    "deposit": "payment",
    "withdrawal": "payment",
    "payment": "payment",
    "invoice": "invoice",
    "credit_note": "credit_note",
}

# Synthetic -> canonical relationship type
RELATIONSHIP_TYPE_MAP: Dict[str, str] = {
    "trades_with": "sells_to",
    "supplies_to": "supplies_to",
    "distributes_for": "distributes_for",
    "manufactures_for": "manufactures_for",
    "sells_to": "sells_to",
    # ownership could be extended; default map keeps existing enums intact
    "owns": "sells_to",
}

@dataclass
class MappingConfig:
    profile_party_type_default: Dict[str, str]
    transaction_type_map: Dict[str, str]
    relationship_type_map: Dict[str, str]


def get_default_mapping() -> MappingConfig:
    return MappingConfig(
        profile_party_type_default=PROFILE_PARTY_TYPE_DEFAULT,
        transaction_type_map=TRANSACTION_TYPE_MAP,
        relationship_type_map=RELATIONSHIP_TYPE_MAP,
    )
