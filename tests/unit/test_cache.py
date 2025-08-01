"""Tests for cache utilities."""

import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from textual_mcp.utils.cache import (
    LRUCache,
    CacheManager,
    cache_key,
    cached,
    cache_manager,
)


class TestLRUCache:
    """Test cases for LRUCache implementation."""

    def test_cache_initialization(self):
        """Test cache initialization with different parameters."""
        # Default initialization
        cache = LRUCache()
        assert cache.max_size == 128
        assert cache.ttl is None
        assert cache.size() == 0

        # Custom initialization
        cache = LRUCache(max_size=50, ttl=10.0)
        assert cache.max_size == 50
        assert cache.ttl == 10.0
        assert cache.size() == 0

    def test_cache_put_and_get(self):
        """Test basic put and get operations."""
        cache = LRUCache[str, str](max_size=3)

        # Put and get values
        cache.put("key1", "value1")
        cache.put("key2", "value2")

        assert cache.get("key1") == "value1"
        assert cache.get("key2") == "value2"
        assert cache.get("key3") is None
        assert cache.get("key3", "default") == "default"
        assert cache.size() == 2

    def test_cache_lru_eviction(self):
        """Test LRU eviction when cache is full."""
        cache = LRUCache[str, str](max_size=3)

        # Fill cache
        cache.put("key1", "value1")
        cache.put("key2", "value2")
        cache.put("key3", "value3")
        assert cache.size() == 3

        # Access key1 to make it recently used
        assert cache.get("key1") == "value1"

        # Add new key, should evict key2 (least recently used)
        cache.put("key4", "value4")
        assert cache.size() == 3
        assert cache.get("key1") == "value1"  # Still present
        assert cache.get("key2") is None  # Evicted
        assert cache.get("key3") == "value3"  # Still present
        assert cache.get("key4") == "value4"  # New key

    def test_cache_update_existing_key(self):
        """Test updating existing key moves it to end."""
        cache = LRUCache[str, str](max_size=3)

        cache.put("key1", "value1")
        cache.put("key2", "value2")
        cache.put("key3", "value3")

        # Update key1
        cache.put("key1", "new_value1")

        # Add new key, should evict key2 (not key1)
        cache.put("key4", "value4")

        assert cache.get("key1") == "new_value1"
        assert cache.get("key2") is None
        assert cache.get("key3") == "value3"
        assert cache.get("key4") == "value4"

    def test_cache_delete(self):
        """Test delete operation."""
        cache = LRUCache[str, str]()

        cache.put("key1", "value1")
        cache.put("key2", "value2")

        # Delete existing key
        assert cache.delete("key1") is True
        assert cache.get("key1") is None
        assert cache.size() == 1

        # Delete non-existing key
        assert cache.delete("key3") is False
        assert cache.size() == 1

    def test_cache_clear(self):
        """Test clear operation."""
        cache = LRUCache[str, str]()

        cache.put("key1", "value1")
        cache.put("key2", "value2")
        cache.put("key3", "value3")
        assert cache.size() == 3

        cache.clear()
        assert cache.size() == 0
        assert cache.get("key1") is None
        assert cache.get("key2") is None
        assert cache.get("key3") is None

    def test_cache_ttl_expiration(self):
        """Test TTL expiration."""
        cache = LRUCache[str, str](ttl=0.1)  # 100ms TTL

        cache.put("key1", "value1")
        assert cache.get("key1") == "value1"

        # Wait for expiration
        time.sleep(0.15)
        assert cache.get("key1") is None

    def test_cache_cleanup_expired(self):
        """Test cleanup_expired method."""
        cache = LRUCache[str, str](ttl=0.1)  # 100ms TTL

        # Add multiple items
        cache.put("key1", "value1")
        cache.put("key2", "value2")
        time.sleep(0.05)  # Wait 50ms
        cache.put("key3", "value3")  # This one is newer

        assert cache.size() == 3

        # Wait for first two to expire (but not the third)
        time.sleep(0.06)  # Total 0.11s for first two, 0.06s for third

        # Cleanup expired
        expired_count = cache.cleanup_expired()
        assert expired_count == 2
        assert cache.size() == 1
        assert cache.get("key3") == "value3"  # Still valid

    def test_cache_no_ttl_cleanup(self):
        """Test cleanup_expired with no TTL set."""
        cache = LRUCache[str, str]()

        cache.put("key1", "value1")
        cache.put("key2", "value2")

        expired_count = cache.cleanup_expired()
        assert expired_count == 0
        assert cache.size() == 2

    def test_cache_thread_safety(self):
        """Test thread safety of cache operations."""
        cache = LRUCache[int, int](max_size=100)
        errors = []

        def worker(start: int, count: int):
            try:
                for i in range(start, start + count):
                    cache.put(i, i * 2)
                    value = cache.get(i)
                    if value is not None and value != i * 2:
                        errors.append(f"Incorrect value for key {i}: {value}")
            except Exception as e:
                errors.append(str(e))

        # Run multiple threads
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = []
            for i in range(10):
                futures.append(executor.submit(worker, i * 10, 10))

            for future in as_completed(futures):
                future.result()

        assert len(errors) == 0
        # Cache should have at most max_size items
        assert cache.size() <= 100


class TestCacheKey:
    """Test cache key generation."""

    def test_cache_key_simple_args(self):
        """Test cache key with simple arguments."""
        key1 = cache_key("arg1", "arg2", 123)
        key2 = cache_key("arg1", "arg2", 123)
        key3 = cache_key("arg1", "arg2", 124)

        assert key1 == key2  # Same args produce same key
        assert key1 != key3  # Different args produce different key

    def test_cache_key_kwargs(self):
        """Test cache key with keyword arguments."""
        key1 = cache_key("arg1", foo="bar", baz=123)
        key2 = cache_key("arg1", baz=123, foo="bar")  # Different order
        key3 = cache_key("arg1", foo="bar", baz=124)

        assert key1 == key2  # Order doesn't matter for kwargs
        assert key1 != key3  # Different values

    def test_cache_key_objects(self):
        """Test cache key with object arguments."""

        class TestObj:
            def __init__(self, value):
                self.value = value

            def __str__(self):
                return f"TestObj({self.value})"

        obj1 = TestObj(42)
        obj2 = TestObj(42)

        key1 = cache_key(obj1)
        key2 = cache_key(obj2)

        # Keys should be same if string representation is same
        assert key1 == key2

    def test_cache_key_mixed_types(self):
        """Test cache key with mixed argument types."""
        key = cache_key("string", 123, [1, 2, 3], {"key": "value"}, arg1="value1", arg2=456)

        # Should produce a valid hash
        assert isinstance(key, str)
        assert len(key) == 32  # MD5 hex digest length


class TestCachedDecorator:
    """Test cached decorator functionality."""

    def test_cached_function(self):
        """Test basic cached function."""
        call_count = 0
        cache = LRUCache[str, int]()

        @cached(cache)
        def expensive_function(x: int) -> int:
            nonlocal call_count
            call_count += 1
            return x * 2

        # First call
        result1 = expensive_function(5)
        assert result1 == 10
        assert call_count == 1

        # Second call should use cache
        result2 = expensive_function(5)
        assert result2 == 10
        assert call_count == 1  # Not called again

        # Different argument
        result3 = expensive_function(6)
        assert result3 == 12
        assert call_count == 2

    def test_cached_with_custom_key_func(self):
        """Test cached decorator with custom key function."""
        cache = LRUCache[str, str]()

        def custom_key_func(name: str, ignore_this: int) -> str:
            # Ignore the second parameter in cache key
            return f"key_{name}"

        @cached(cache, key_func=custom_key_func)
        def get_greeting(name: str, ignore_this: int) -> str:
            return f"Hello, {name}! (param: {ignore_this})"

        result1 = get_greeting("Alice", 1)
        result2 = get_greeting("Alice", 2)  # Different param but same key

        assert result1 == result2  # Same cached result
        assert result1 == "Hello, Alice! (param: 1)"

    def test_cached_decorator_attributes(self):
        """Test that cached decorator adds cache management attributes."""
        cache = LRUCache[str, int]()

        @cached(cache)
        def my_function(x: int) -> int:
            return x * 2

        # Check attributes
        assert hasattr(my_function, "cache")
        assert my_function.cache is cache

        assert hasattr(my_function, "cache_clear")
        assert hasattr(my_function, "cache_info")

        # Test cache_info
        my_function(5)
        my_function(6)

        info = my_function.cache_info()
        assert info["size"] == 2
        assert info["max_size"] == 128
        assert info["ttl"] is None

        # Test cache_clear
        my_function.cache_clear()
        info = my_function.cache_info()
        assert info["size"] == 0


class TestCacheManager:
    """Test CacheManager functionality."""

    def test_cache_manager_create_cache(self):
        """Test creating named caches."""
        manager = CacheManager()

        cache1 = manager.create_cache("cache1", max_size=50, ttl=60)
        cache2 = manager.create_cache("cache2", max_size=100)

        assert isinstance(cache1, LRUCache)
        assert cache1.max_size == 50
        assert cache1.ttl == 60

        assert isinstance(cache2, LRUCache)
        assert cache2.max_size == 100
        assert cache2.ttl is None

    def test_cache_manager_get_cache(self):
        """Test getting caches by name."""
        manager = CacheManager()

        cache1 = manager.create_cache("test_cache")
        retrieved = manager.get_cache("test_cache")

        assert retrieved is cache1
        assert manager.get_cache("nonexistent") is None

    def test_cache_manager_clear_all(self):
        """Test clearing all caches."""
        manager = CacheManager()

        cache1 = manager.create_cache("cache1")
        cache2 = manager.create_cache("cache2")

        cache1.put("key", "value")
        cache2.put("key", "value")

        assert cache1.size() == 1
        assert cache2.size() == 1

        manager.clear_all()

        assert cache1.size() == 0
        assert cache2.size() == 0

    def test_cache_manager_cleanup_expired(self):
        """Test cleaning up expired items from all caches."""
        manager = CacheManager()

        cache1 = manager.create_cache("cache1", ttl=0.1)
        cache2 = manager.create_cache("cache2", ttl=0.1)
        cache3 = manager.create_cache("cache3")  # No TTL

        # Add items
        cache1.put("key1", "value1")
        cache2.put("key2", "value2")
        cache3.put("key3", "value3")

        # Wait for expiration
        time.sleep(0.15)

        results = manager.cleanup_all_expired()

        assert results["cache1"] == 1
        assert results["cache2"] == 1
        assert results["cache3"] == 0

        assert cache1.size() == 0
        assert cache2.size() == 0
        assert cache3.size() == 1

    def test_cache_manager_get_stats(self):
        """Test getting statistics for all caches."""
        manager = CacheManager()

        cache1 = manager.create_cache("cache1", max_size=50, ttl=60)
        cache2 = manager.create_cache("cache2", max_size=100)

        cache1.put("key1", "value1")
        cache1.put("key2", "value2")
        cache2.put("key1", "value1")

        stats = manager.get_stats()

        assert stats["cache1"]["size"] == 2
        assert stats["cache1"]["max_size"] == 50
        assert stats["cache1"]["ttl"] == 60

        assert stats["cache2"]["size"] == 1
        assert stats["cache2"]["max_size"] == 100
        assert stats["cache2"]["ttl"] is None


class TestGlobalCacheManager:
    """Test the global cache manager instance."""

    def test_global_cache_manager_exists(self):
        """Test that global cache manager is available."""

        assert isinstance(cache_manager, CacheManager)

    def test_default_caches_exist(self):
        """Test that default caches are created."""
        from textual_mcp.utils.cache import (
            css_validation_cache,
            documentation_cache,
            embedding_cache,
        )

        assert isinstance(css_validation_cache, LRUCache)
        assert css_validation_cache.max_size == 100
        assert css_validation_cache.ttl == 3600

        assert isinstance(documentation_cache, LRUCache)
        assert documentation_cache.max_size == 50
        assert documentation_cache.ttl == 7200

        assert isinstance(embedding_cache, LRUCache)
        assert embedding_cache.max_size == 200
        assert embedding_cache.ttl == 86400
