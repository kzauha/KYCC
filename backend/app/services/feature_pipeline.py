from __future__ import annotations

from typing import Any, Dict

from app.adapters.registry import get_adapter_registry
from app.cache.ttl_cache import TTLCache
from app.cache.cache_key import generate_cache_key


class FeaturePipeline:
    """Synchronous feature ingestion pipeline integrating adapters and TTL cache."""

    def __init__(self, ttl_seconds: int = 300) -> None:
        self.cache = TTLCache(ttl_seconds=ttl_seconds)

    def ingest(self, source_type: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch data from adapter, cache by party+source key, and return payload.

        Cache key format uses party_id and source_type to avoid cross-source collisions.
        """
        party_id = str(params.get("party_id", "unknown"))
        cache_key = generate_cache_key(party_id, f"src:{source_type}")

        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

        adapter = get_adapter_registry().get(source_type)
        payload = adapter.parse(params)

        # Basic normalization hook — could expand later for DB models
        normalized = {
            "party": payload.get("party", {}),
            "accounts": payload.get("accounts", []),
            "transactions": payload.get("transactions", []),
            "relationships": payload.get("relationships", []),
        }

        self.cache.set(cache_key, normalized)
        return normalized


# Singleton accessor for ease of use
_pipeline: FeaturePipeline | None = None


def get_feature_pipeline(ttl_seconds: int = 300) -> FeaturePipeline:
    global _pipeline
    if _pipeline is None:
        _pipeline = FeaturePipeline(ttl_seconds=ttl_seconds)
    return _pipeline
