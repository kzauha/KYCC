"""Cache key generation logic."""


def generate_cache_key(party_id: int, feature_set: str = "all") -> str:
    """
    Generate a cache key for party features.
    
    Args:
        party_id: The party identifier
        feature_set: Type of features ('all', 'kyc', 'transaction', 'network')
    
    Returns:
        Cache key string
    
    Example:
        >>> generate_cache_key(42, "all")
        "party:42:features:all"
    """
    return f"party:{party_id}:features:{feature_set}"


def generate_score_cache_key(party_id: int, model_version: str = "v1.0") -> str:
    """
    Generate a cache key for party score.
    
    Args:
        party_id: The party identifier
        model_version: The scoring model version
    
    Returns:
        Cache key string
    
    Example:
        >>> generate_score_cache_key(42, "v1.0")
        "party:42:score:v1.0"
    """
    return f"party:{party_id}:score:{model_version}"
