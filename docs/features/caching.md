# Feature Caching

KYCC implements a TTL (Time-To-Live) cache for feature lookups to improve performance.

## Overview

| Property | Value |
|----------|-------|
| Location | `backend/app/cache/ttl_cache.py` |
| Default TTL | 300 seconds (5 minutes) |
| Thread Safety | Yes (threading.Lock) |
| Storage | In-memory dictionary |

---

## Cache Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        TTL Cache                                    │
│                                                                     │
│   ┌─────────────────────────────────────────────────────────────┐  │
│   │  Key: "party:123:features:all"                              │  │
│   │  Value: {                                                   │  │
│   │    "features": [...],                                       │  │
│   │    "timestamp": 1703001234.567                              │  │
│   │  }                                                          │  │
│   └─────────────────────────────────────────────────────────────┘  │
│                                                                     │
│   ┌─────────────────────────────────────────────────────────────┐  │
│   │  Key: "party:456:features:all"                              │  │
│   │  Value: {...}                                               │  │
│   └─────────────────────────────────────────────────────────────┘  │
│                                                                     │
│   Thread Lock: threading.Lock()                                     │
│   TTL Check: current_time - timestamp > ttl                         │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Implementation

```python
import threading
import time
from typing import Any, Optional

class TTLCache:
    """Thread-safe in-memory cache with TTL expiration."""
    
    def __init__(self, default_ttl: int = 300):
        """
        Initialize cache.
        
        Args:
            default_ttl: Default time-to-live in seconds
        """
        self._cache = {}
        self._lock = threading.Lock()
        self._default_ttl = default_ttl
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache if not expired.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if expired/missing
        """
        with self._lock:
            if key not in self._cache:
                return None
            
            entry = self._cache[key]
            if time.time() - entry['timestamp'] > entry['ttl']:
                # Expired - remove and return None
                del self._cache[key]
                return None
            
            return entry['value']
    
    def set(self, key: str, value: Any, ttl: int = None):
        """
        Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Optional TTL override
        """
        with self._lock:
            self._cache[key] = {
                'value': value,
                'timestamp': time.time(),
                'ttl': ttl or self._default_ttl
            }
    
    def delete(self, key: str):
        """Remove key from cache."""
        with self._lock:
            self._cache.pop(key, None)
    
    def clear(self):
        """Clear all cached entries."""
        with self._lock:
            self._cache.clear()
    
    def cleanup(self):
        """Remove all expired entries."""
        with self._lock:
            current_time = time.time()
            expired_keys = [
                key for key, entry in self._cache.items()
                if current_time - entry['timestamp'] > entry['ttl']
            ]
            for key in expired_keys:
                del self._cache[key]
```

---

## Key Format

Cache keys follow a consistent pattern:

```
party:{party_id}:features:all
```

Examples:
- `party:123:features:all`
- `party:456:features:all`

---

## Usage in Feature Pipeline

```python
from app.cache.ttl_cache import TTLCache

# Global cache instance
feature_cache = TTLCache(default_ttl=300)

def get_features_for_party(party_id: int, db: Session) -> dict:
    """Get features with caching."""
    cache_key = f"party:{party_id}:features:all"
    
    # Check cache first
    cached = feature_cache.get(cache_key)
    if cached:
        return cached
    
    # Cache miss - extract features
    pipeline = FeaturePipelineService(db)
    features = pipeline.extract_all_features(party_id)
    
    # Store in cache
    feature_cache.set(cache_key, features)
    
    return features
```

---

## Cache Invalidation

### Automatic Expiration

Entries automatically expire after TTL:

```python
# Entry created at T=0
cache.set("key", value, ttl=300)

# At T=299, entry is valid
cache.get("key")  # Returns value

# At T=301, entry is expired
cache.get("key")  # Returns None (and deletes entry)
```

### Manual Invalidation

Invalidate when features are recomputed:

```python
def update_features(party_id: int, db: Session):
    """Recompute features and invalidate cache."""
    # Invalidate cache
    cache_key = f"party:{party_id}:features:all"
    feature_cache.delete(cache_key)
    
    # Recompute
    pipeline = FeaturePipelineService(db)
    return pipeline.extract_all_features(party_id)
```

### Batch Invalidation

Invalidate all entries for a batch:

```python
def invalidate_batch(batch_id: str, db: Session):
    """Invalidate cache for all parties in batch."""
    parties = db.query(Party.id).filter(Party.batch_id == batch_id).all()
    
    for (party_id,) in parties:
        cache_key = f"party:{party_id}:features:all"
        feature_cache.delete(cache_key)
```

---

## Configuration

### TTL Configuration

Default TTL can be configured:

```python
# Short TTL for frequently changing data
volatile_cache = TTLCache(default_ttl=60)  # 1 minute

# Long TTL for stable data
stable_cache = TTLCache(default_ttl=3600)  # 1 hour

# Per-key TTL override
cache.set("key", value, ttl=120)  # 2 minutes
```

### Memory Limits

Current implementation has no memory limits. For production:

```python
class BoundedTTLCache(TTLCache):
    def __init__(self, default_ttl: int = 300, max_size: int = 1000):
        super().__init__(default_ttl)
        self._max_size = max_size
    
    def set(self, key: str, value: Any, ttl: int = None):
        with self._lock:
            # Evict oldest if at capacity
            if len(self._cache) >= self._max_size:
                oldest = min(self._cache.items(), key=lambda x: x[1]['timestamp'])
                del self._cache[oldest[0]]
            
            super().set(key, value, ttl)
```

---

## Thread Safety

The cache uses `threading.Lock()` for thread safety:

```python
# Multiple threads can safely read/write
import threading

def worker(party_id):
    features = get_features_for_party(party_id, db)
    # Process features

threads = [
    threading.Thread(target=worker, args=(i,))
    for i in range(10)
]

for t in threads:
    t.start()

for t in threads:
    t.join()
```

---

## Monitoring

### Cache Statistics

```python
class TTLCache:
    def __init__(self, default_ttl: int = 300):
        # ...
        self._hits = 0
        self._misses = 0
    
    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            if key in self._cache and not expired:
                self._hits += 1
                return entry['value']
            else:
                self._misses += 1
                return None
    
    def stats(self) -> dict:
        with self._lock:
            total = self._hits + self._misses
            return {
                'hits': self._hits,
                'misses': self._misses,
                'hit_rate': self._hits / total if total > 0 else 0,
                'size': len(self._cache)
            }
```

---

## Best Practices

1. **Use consistent key formats**: Always use `party:{id}:features:all`
2. **Invalidate on updates**: Clear cache when features are recomputed
3. **Tune TTL**: Balance freshness vs. database load
4. **Monitor hit rate**: Low hit rate indicates TTL too short
5. **Handle cache failures gracefully**: Fall back to database on cache errors
