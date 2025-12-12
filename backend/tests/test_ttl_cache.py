"""Unit tests for TTL Cache module."""
import time
import pytest
from app.cache import TTLCache, generate_cache_key, generate_score_cache_key


class TestCacheKey:
    """Test cache key generation."""
    
    def test_generate_feature_cache_key(self):
        """Test feature cache key generation."""
        key = generate_cache_key(42, "all")
        assert key == "party:42:features:all"
    
    def test_generate_feature_cache_key_with_type(self):
        """Test feature cache key with specific feature type."""
        key = generate_cache_key(99, "kyc")
        assert key == "party:99:features:kyc"
    
    def test_generate_score_cache_key(self):
        """Test score cache key generation."""
        key = generate_score_cache_key(42, "v1.0")
        assert key == "party:42:score:v1.0"
    
    def test_generate_score_cache_key_default_version(self):
        """Test score cache key with default version."""
        key = generate_score_cache_key(123)
        assert key == "party:123:score:v1.0"


class TestTTLCache:
    """Test TTL Cache functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.cache = TTLCache(ttl_seconds=2)  # 2 seconds for faster testing
        self.test_features = {"kyc_score": 85, "transaction_count": 47}
    
    def test_cache_set_and_get(self):
        """Test basic set and get operations."""
        key = generate_cache_key(42, "all")
        self.cache.set(key, self.test_features)
        
        result = self.cache.get(key)
        assert result == self.test_features
    
    def test_cache_miss_nonexistent_key(self):
        """Test that getting a non-existent key returns None."""
        result = self.cache.get("nonexistent:key")
        assert result is None
    
    def test_cache_expiry_after_ttl(self):
        """Test that cache entries expire after TTL."""
        key = generate_cache_key(42, "all")
        self.cache.set(key, self.test_features)
        
        # Verify cache hit within TTL
        assert self.cache.get(key) is not None
        
        # Wait for TTL to expire
        time.sleep(2.1)
        
        # Verify cache miss after TTL
        assert self.cache.get(key) is None
    
    def test_cache_hit_within_ttl(self):
        """Test that cache hit occurs within TTL window."""
        key = generate_cache_key(42, "all")
        self.cache.set(key, self.test_features)
        
        # Access within TTL
        time.sleep(0.5)
        result = self.cache.get(key)
        
        assert result == self.test_features
    
    def test_cache_manual_clear(self):
        """Test manual cache invalidation."""
        key = generate_cache_key(42, "all")
        self.cache.set(key, self.test_features)
        
        # Verify cache hit
        assert self.cache.get(key) is not None
        
        # Manually clear
        self.cache.clear(key)
        
        # Verify cache miss
        assert self.cache.get(key) is None
    
    def test_cache_clear_party(self):
        """Test clearing all entries for a specific party."""
        party_id = 42
        
        # Set multiple cache entries for same party
        cache_key_features = generate_cache_key(party_id, "all")
        cache_key_score = generate_score_cache_key(party_id, "v1.0")
        
        self.cache.set(cache_key_features, self.test_features)
        self.cache.set(cache_key_score, {"score": 750})
        
        # Verify both cached
        assert self.cache.get(cache_key_features) is not None
        assert self.cache.get(cache_key_score) is not None
        
        # Clear all for party
        self.cache.clear_party(party_id)
        
        # Verify both cleared
        assert self.cache.get(cache_key_features) is None
        assert self.cache.get(cache_key_score) is None
    
    def test_cache_clear_party_does_not_affect_other_parties(self):
        """Test that clearing one party doesn't affect others."""
        party_1_key = generate_cache_key(1, "all")
        party_2_key = generate_cache_key(2, "all")
        
        self.cache.set(party_1_key, {"kyc_score": 85})
        self.cache.set(party_2_key, {"kyc_score": 60})
        
        # Clear party 1
        self.cache.clear_party(1)
        
        # Verify party 1 cleared, party 2 intact
        assert self.cache.get(party_1_key) is None
        assert self.cache.get(party_2_key) == {"kyc_score": 60}
    
    def test_cache_clear_all(self):
        """Test clearing entire cache."""
        key1 = generate_cache_key(1, "all")
        key2 = generate_cache_key(2, "all")
        
        self.cache.set(key1, self.test_features)
        self.cache.set(key2, self.test_features)
        
        # Verify populated
        assert self.cache.size() == 2
        
        # Clear all
        self.cache.clear_all()
        
        # Verify empty
        assert self.cache.size() == 0
        assert self.cache.get(key1) is None
        assert self.cache.get(key2) is None
    
    def test_cache_size(self):
        """Test cache size tracking."""
        assert self.cache.size() == 0
        
        self.cache.set(generate_cache_key(1, "all"), self.test_features)
        assert self.cache.size() == 1
        
        self.cache.set(generate_cache_key(2, "all"), self.test_features)
        assert self.cache.size() == 2
        
        self.cache.clear_all()
        assert self.cache.size() == 0
    
    def test_cache_stats(self):
        """Test cache statistics."""
        self.cache.set(generate_cache_key(1, "all"), self.test_features)
        
        stats = self.cache.stats()
        assert stats["size"] == 1
        assert stats["ttl_seconds"] == 2
    
    def test_cache_prune_expired(self):
        """Test pruning expired entries."""
        key1 = generate_cache_key(1, "all")
        key2 = generate_cache_key(2, "all")
        
        self.cache.set(key1, self.test_features)
        self.cache.set(key2, self.test_features)
        
        # Wait for expiry
        time.sleep(2.1)
        
        # Prune and verify count
        removed = self.cache.prune_expired()
        assert removed == 2
        assert self.cache.size() == 0
    
    def test_cache_prune_preserves_valid_entries(self):
        """Test that pruning only removes expired entries."""
        key1 = generate_cache_key(1, "all")
        key2 = generate_cache_key(2, "all")
        
        # Set with short TTL
        cache_short = TTLCache(ttl_seconds=1)
        cache_short.set(key1, self.test_features)
        
        # Wait a bit
        time.sleep(0.5)
        
        # Set another entry (should not expire)
        cache_short.set(key2, self.test_features)
        
        # Wait for first to expire
        time.sleep(0.6)
        
        # Prune
        removed = cache_short.prune_expired()
        
        # Only first should be expired
        assert removed == 1
        assert cache_short.get(key1) is None
        assert cache_short.get(key2) is not None
    
    def test_cache_update_refreshes_timestamp(self):
        """Test that updating a value refreshes its TTL."""
        key = generate_cache_key(42, "all")
        cache = TTLCache(ttl_seconds=2)
        
        # Set initial value
        cache.set(key, {"kyc_score": 85})
        
        # Wait partially through TTL
        time.sleep(1)
        
        # Update value (should refresh timestamp)
        cache.set(key, {"kyc_score": 90})
        
        # Wait more than original TTL from first set
        time.sleep(1.5)
        
        # Should still be in cache (due to refresh)
        result = cache.get(key)
        assert result == {"kyc_score": 90}
    
    def test_cache_thread_safety(self):
        """Test that cache operations are thread-safe."""
        import threading
        
        key = generate_cache_key(42, "all")
        cache = TTLCache(ttl_seconds=5)
        results = []
        
        def write_cache():
            for i in range(10):
                cache.set(f"{key}:{i}", {"value": i})
        
        def read_cache():
            for i in range(10):
                result = cache.get(f"{key}:{i}")
                results.append(result)
        
        # Run concurrent operations
        t1 = threading.Thread(target=write_cache)
        t2 = threading.Thread(target=read_cache)
        
        t1.start()
        t2.start()
        t1.join()
        t2.join()
        
        # Verify no exceptions and cache populated
        assert cache.size() >= 5  # At least some items should be cached
    
    def test_cache_with_large_values(self):
        """Test cache with large data structures."""
        key = generate_cache_key(42, "all")
        
        # Create large feature dict
        large_features = {f"feature_{i}": i * 1.5 for i in range(100)}
        
        self.cache.set(key, large_features)
        result = self.cache.get(key)
        
        assert result == large_features
        assert len(result) == 100
    
    def test_cache_with_custom_ttl(self):
        """Test cache with custom TTL."""
        cache = TTLCache(ttl_seconds=1)
        key = generate_cache_key(42, "all")
        
        cache.set(key, self.test_features)
        
        # Should be available immediately
        assert cache.get(key) is not None
        
        # Wait for expiry
        time.sleep(1.1)
        
        # Should be expired
        assert cache.get(key) is None


class TestCacheRealWorldUsage:
    """Test real-world usage scenarios."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.cache = TTLCache(ttl_seconds=300)  # 5 minutes
    
    def test_party_feature_caching_workflow(self):
        """Test typical party feature caching workflow."""
        party_id = 42
        features_key = generate_cache_key(party_id, "all")
        score_key = generate_score_cache_key(party_id, "v1.0")
        
        # Simulate scoring pipeline: extract features, compute score
        features = {
            "kyc_score": 85,
            "transaction_count": 47,
            "network_size": 12,
            "company_age_days": 1850
        }
        
        # Cache features and score
        self.cache.set(features_key, features)
        self.cache.set(score_key, 750)
        
        # Subsequent requests use cache
        assert self.cache.get(features_key) == features
        assert self.cache.get(score_key) == 750
    
    def test_transaction_posted_invalidation_workflow(self):
        """Test cache invalidation when transaction posted."""
        party_id = 42
        features_key = generate_cache_key(party_id, "all")
        score_key = generate_score_cache_key(party_id, "v1.0")
        
        # Initial scoring
        self.cache.set(features_key, {"transaction_count": 47})
        self.cache.set(score_key, 750)
        
        # Transaction posted
        self.cache.clear_party(party_id)
        
        # Cache should be empty, triggering re-computation
        assert self.cache.get(features_key) is None
        assert self.cache.get(score_key) is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
