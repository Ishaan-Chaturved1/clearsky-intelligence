import time
from typing import Dict, Any, Optional
from pydantic import BaseModel

class SourceFetchResult(BaseModel):
    source_name: str
    is_success: bool
    data: Optional[Any] = None
    error_message: Optional[str] = None
    is_cached: bool = False
    is_fallback: bool = False
    fetched_at: float

class SimpleTTLCache:
    def __init__(self, default_ttl_seconds: int = 1800):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self.default_ttl = default_ttl_seconds

    def get(self, key: str) -> Optional[Any]:
        if key in self._cache:
            entry = self._cache[key]
            if time.time() - entry["timestamp"] < entry["ttl"]:
                return entry["data"]
            else:
                del self._cache[key]
        return None

    def set(self, key: str, data: Any, ttl_seconds: Optional[int] = None) -> None:
        self._cache[key] = {
            "data": data,
            "timestamp": time.time(),
            "ttl": ttl_seconds if ttl_seconds is not None else self.default_ttl
        }

    def clear(self) -> None:
        self._cache.clear()

global_cache = SimpleTTLCache(default_ttl_seconds=1800)
