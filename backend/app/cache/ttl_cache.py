"""Time-To-Live (TTL) Cache implementation with 5-minute expiry."""
from datetime import datetime, timedelta
from typing import Any, Optional, Dict
import threading


class TTLCache:
    """
    In-memory cache with configurable time-to-live (TTL) expiry.
    
    Thread-safe cache that stores values with timestamps and automatically
    invalidates entries after TTL seconds.
    
    Attributes:
        ttl_seconds: Time-to-live duration in seconds (default: 300 = 5 minutes)
    
    Example:
        >>> cache = TTLCache(ttl_seconds=300)
        >>> cache.set("party:42:features:all", {"kyc_score": 85})
        >>> features = cache.get("party:42:features:all")
        >>> print(features)
        {"kyc_score": 85}
    """
    
    def __init__(self, ttl_seconds: int = 300):
        """
        Initialize TTL cache.
        
        Args:
            ttl_seconds: Time-to-live in seconds (default: 300 = 5 minutes)
        """
        self.ttl_seconds = ttl_seconds
        self._cache: Dict[str, tuple] = {}  # {key: (value, timestamp)}
        self._lock = threading.Lock()
    
    def set(self, key: str, value: Any) -> None:
        """
        Store a value in cache with current timestamp.
        
        Args:
            key: Cache key (e.g., "party:42:features:all")
            value: Value to cache (typically dict of features)
        
        Thread-safe.
        
        Example:
            >>> cache.set("party:42:features:all", {"kyc_score": 85})
        """
        with self._lock:
            self._cache[key] = (value, datetime.utcnow())
    
    def get(self, key: str) -> Optional[Any]:
        """
        Retrieve a value from cache if it exists and hasn't expired.
        
        Args:
            key: Cache key
        
        Returns:
            Cached value if key exists and TTL not exceeded, None otherwise
        
        Thread-safe.
        
        Example:
            >>> features = cache.get("party:42:features:all")
            >>> if features:
            ...     print(f"Cache hit: {features}")
            ... else:
            ...     print("Cache miss or expired")
        """
        with self._lock:
            if key not in self._cache:
                return None
            
            value, timestamp = self._cache[key]
            age = (datetime.utcnow() - timestamp).total_seconds()
            
            if age > self.ttl_seconds:
                # Expired, remove and return None
                del self._cache[key]
                return None
            
            return value
    
    def clear(self, key: str) -> None:
        """
        Manually invalidate a cache entry.
        
        Used when upstream data changes (e.g., new transaction posted).
        
        Args:
            key: Cache key to invalidate
        
        Thread-safe.
        
        Example:
            >>> # Transaction posted for Party 42
            >>> cache.clear("party:42:features:all")
            >>> cache.clear("party:42:score:v1.0")
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
    
    def clear_party(self, party_id: int) -> None:
        """
        Invalidate all cache entries for a specific party.
        
        Useful when transaction data changes.
        
        Args:
            party_id: Party ID to clear
        
        Thread-safe.
        
        Example:
            >>> # New transaction posted
            >>> cache.clear_party(42)
        """
        with self._lock:
            keys_to_delete = [k for k in self._cache.keys() if f"party:{party_id}:" in k]
            for key in keys_to_delete:
                del self._cache[key]
    
    def clear_all(self) -> None:
        """
        Clear all cache entries.
        
        Useful for testing or full reset.
        
        Thread-safe.
        """
        with self._lock:
            self._cache.clear()
    
    def size(self) -> int:
        """
        Get current number of items in cache.
        
        Returns:
            Count of cached items
        """
        with self._lock:
            return len(self._cache)
    
    def stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dict with 'size' and 'ttl_seconds' keys
        
        Example:
            >>> stats = cache.stats()
            >>> print(f"Cache: {stats['size']} items, TTL: {stats['ttl_seconds']}s")
            Cache: 5 items, TTL: 300s
        """
        with self._lock:
            return {
                "size": len(self._cache),
                "ttl_seconds": self.ttl_seconds
            }
    
    def prune_expired(self) -> int:
        """
        Remove all expired entries from cache.
        
        Called periodically to clean up stale data.
        
        Returns:
            Number of entries removed
        
        Thread-safe.
        """
        with self._lock:
            now = datetime.utcnow()
            expired_keys = []
            
            for key, (value, timestamp) in self._cache.items():
                age = (now - timestamp).total_seconds()
                if age > self.ttl_seconds:
                    expired_keys.append(key)
            
            for key in expired_keys:
                del self._cache[key]
            
            return len(expired_keys)
