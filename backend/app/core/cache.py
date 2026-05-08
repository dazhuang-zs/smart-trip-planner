"""LRU 内存缓存"""
import time
from typing import Any, Optional, Callable
from collections import OrderedDict
from threading import RLock


class LRUCache:
    """线程安全的 LRU 缓存，支持 TTL"""

    def __init__(self, max_size: int = 2000, default_ttl: int = 86400):
        self._cache: OrderedDict = OrderedDict()
        self._expiry: dict = {}
        self._max_size = max_size
        self._default_ttl = default_ttl
        self._lock = RLock()

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            if key not in self._cache or time.time() > self._expiry.get(key, 0):
                return None
            self._cache.move_to_end(key)
            return self._cache[key]

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        with self._lock:
            self._cache.pop(key, None)
            self._expiry.pop(key, None)
            while len(self._cache) >= self._max_size:
                self._cache.popitem(last=False)
            self._cache[key] = value
            self._expiry[key] = time.time() + (ttl or self._default_ttl)

    def delete(self, key: str) -> None:
        with self._lock:
            self._cache.pop(key, None)
            self._expiry.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()
            self._expiry.clear()

    def get_or_compute(self, key: str, fn: Callable[[], Any], ttl: Optional[int] = None) -> Any:
        v = self.get(key)
        if v is None:
            v = fn()
            self.set(key, v, ttl)
        return v


# 全局缓存实例
poi_cache = LRUCache(max_size=2000, default_ttl=86400)
distance_cache = LRUCache(max_size=5000, default_ttl=3600)
geocode_cache = LRUCache(max_size=1000, default_ttl=86400 * 7)


def get_poi_cache() -> LRUCache:
    """获取 POI 缓存实例"""
    return poi_cache


def get_distance_cache() -> LRUCache:
    """获取距离缓存实例"""
    return distance_cache


def get_geocode_cache() -> LRUCache:
    """获取地理编码缓存实例"""
    return geocode_cache
