"""Caching utilities for Textual MCP Server."""

import time
import threading
from typing import Any, Dict, Optional, Tuple, Generic, TypeVar, Callable, cast
from collections import OrderedDict
from functools import wraps
from hashlib import md5

K = TypeVar("K")
V = TypeVar("V")
R = TypeVar("R")
F = TypeVar("F", bound=Callable[..., Any])


class LRUCache(Generic[K, V]):
    """Thread-safe LRU (Least Recently Used) cache implementation."""

    def __init__(self, max_size: int = 128, ttl: Optional[float] = None):
        """
        Initialize LRU cache.

        Args:
            max_size: Maximum number of items to store
            ttl: Time-to-live in seconds (None for no expiration)
        """
        self.max_size = max_size
        self.ttl = ttl
        self._cache: OrderedDict[K, Tuple[V, float]] = OrderedDict()
        self._lock = threading.RLock()

    def get(self, key: K, default: Optional[V] = None) -> Optional[V]:
        """Get value from cache."""
        with self._lock:
            if key not in self._cache:
                return default

            value, timestamp = self._cache[key]

            # Check if expired
            if self.ttl and time.time() - timestamp > self.ttl:
                del self._cache[key]
                return default

            # Move to end (most recently used)
            self._cache.move_to_end(key)
            return value

    def put(self, key: K, value: V) -> None:
        """Put value in cache."""
        with self._lock:
            current_time = time.time()

            if key in self._cache:
                # Update existing key
                self._cache[key] = (value, current_time)
                self._cache.move_to_end(key)
            else:
                # Add new key
                self._cache[key] = (value, current_time)

                # Remove oldest if over capacity
                if len(self._cache) > self.max_size:
                    self._cache.popitem(last=False)

    def delete(self, key: K) -> bool:
        """Delete key from cache."""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    def clear(self) -> None:
        """Clear all items from cache."""
        with self._lock:
            self._cache.clear()

    def size(self) -> int:
        """Get current cache size."""
        with self._lock:
            return len(self._cache)

    def cleanup_expired(self) -> int:
        """Remove expired items and return count of removed items."""
        if not self.ttl:
            return 0

        with self._lock:
            current_time = time.time()
            expired_keys = []

            for key, (_, timestamp) in self._cache.items():
                if current_time - timestamp > self.ttl:
                    expired_keys.append(key)

            for key in expired_keys:
                del self._cache[key]

            return len(expired_keys)


def cache_key(*args: Any, **kwargs: Any) -> str:
    """Generate a cache key from function arguments."""
    # Convert arguments to a string representation
    key_parts = []

    # Add positional arguments
    for arg in args:
        if hasattr(arg, "__dict__"):
            # For objects, use their string representation
            key_parts.append(str(arg))
        else:
            key_parts.append(repr(arg))

    # Add keyword arguments (sorted for consistency)
    for k, v in sorted(kwargs.items()):
        key_parts.append(f"{k}={repr(v)}")

    # Create hash of the key parts
    key_string = "|".join(key_parts)
    return md5(key_string.encode()).hexdigest()


class CachedFunctionWrapper(Generic[R]):
    """Wrapper for cached functions with cache management methods."""

    def __init__(
        self,
        func: Callable[..., R],
        cache: LRUCache[str, Any],
        key_func: Optional[Callable[..., str]] = None,
    ):
        self._func = func
        self.cache: LRUCache[str, Any] = cache
        self._key_func = key_func
        self.cache_clear = cache.clear
        self.cache_info = lambda: {
            "size": cache.size(),
            "max_size": cache.max_size,
            "ttl": cache.ttl,
        }
        wraps(func)(self)

    def __call__(self, *args: Any, **kwargs: Any) -> R:
        # Generate cache key
        if self._key_func:
            key = self._key_func(*args, **kwargs)
        else:
            key = cache_key(*args, **kwargs)

        # Try to get from cache
        cached_result = self.cache.get(key)
        if cached_result is not None:
            return cast(R, cached_result)

        # Execute function and cache result
        result = self._func(*args, **kwargs)
        self.cache.put(key, result)
        return result


def cached(
    cache: LRUCache[str, Any], key_func: Optional[Callable[..., str]] = None
) -> Callable[[F], F]:
    """
    Decorator to cache function results.

    Args:
        cache: LRUCache instance to use
        key_func: Function to generate cache key (default: use cache_key)
    """

    def decorator(func: F) -> F:
        wrapper = CachedFunctionWrapper(func, cache, key_func)
        return cast(F, wrapper)

    return decorator


class CacheManager:
    """Manages multiple caches for different purposes."""

    def __init__(self) -> None:
        self._caches: Dict[str, LRUCache] = {}

    def create_cache(self, name: str, max_size: int = 128, ttl: Optional[float] = None) -> LRUCache:
        """Create a new named cache."""
        cache: LRUCache[Any, Any] = LRUCache(max_size=max_size, ttl=ttl)
        self._caches[name] = cache
        return cache

    def get_cache(self, name: str) -> Optional[LRUCache]:
        """Get a cache by name."""
        return self._caches.get(name)

    def clear_all(self) -> None:
        """Clear all caches."""
        for cache in self._caches.values():
            cache.clear()

    def cleanup_all_expired(self) -> Dict[str, int]:
        """Cleanup expired items from all caches."""
        results = {}
        for name, cache in self._caches.items():
            results[name] = cache.cleanup_expired()
        return results

    def get_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all caches."""
        stats = {}
        for name, cache in self._caches.items():
            stats[name] = {
                "size": cache.size(),
                "max_size": cache.max_size,
                "ttl": cache.ttl,
            }
        return stats


# Global cache manager instance
cache_manager = CacheManager()

# Create default caches
css_validation_cache = cache_manager.create_cache(
    "css_validation",
    max_size=100,
    ttl=3600,  # 1 hour
)

documentation_cache = cache_manager.create_cache(
    "documentation",
    max_size=50,
    ttl=7200,  # 2 hours
)

embedding_cache = cache_manager.create_cache(
    "embeddings",
    max_size=200,
    ttl=86400,  # 24 hours
)
