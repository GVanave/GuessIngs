"""Fixed-window rate limiting (in-memory, or Redis when REDIS_URL is set)."""

from __future__ import annotations

import threading
import time
from collections.abc import Callable

from fastapi import Request

from app.core.config import get_settings
from app.core.errors import AppError


class _MemoryBackend:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._hits: dict[str, tuple[int, int]] = {}

    def hit(self, key: str, window: int) -> int:
        now_window = int(time.time() // window)
        with self._lock:
            start, count = self._hits.get(key, (now_window, 0))
            if start != now_window:
                start, count = now_window, 0
            count += 1
            self._hits[key] = (start, count)
            if len(self._hits) > 50_000:  # bound memory
                self._hits = {k: v for k, v in self._hits.items() if v[0] == now_window}
            return count

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


class _RedisBackend:
    def __init__(self, url: str) -> None:
        import redis

        self._redis = redis.Redis.from_url(url, socket_timeout=1)

    def hit(self, key: str, window: int) -> int:
        bucket = f"rl:{key}:{int(time.time() // window)}"
        pipe = self._redis.pipeline()
        pipe.incr(bucket)
        pipe.expire(bucket, window)
        count, _ = pipe.execute()
        return int(count)

    def reset(self) -> None:  # pragma: no cover
        pass


_backend: _MemoryBackend | _RedisBackend | None = None


def backend():
    global _backend
    if _backend is None:
        url = get_settings().redis_url
        _backend = _RedisBackend(url) if url else _MemoryBackend()
    return _backend


def reset_rate_limits() -> None:
    backend().reset()


def client_ip(request: Request) -> str:
    if get_settings().trust_proxy:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def rate_limit(scope: str, setting_name: str, window: int = 60) -> Callable:
    def dependency(request: Request) -> None:
        limit = getattr(get_settings(), setting_name)
        key = f"{scope}:{client_ip(request)}"
        try:
            count = backend().hit(key, window)
        except Exception:  # never fail requests because the limiter store is down
            return
        if count > limit:
            raise AppError(
                429, "rate_limited", "Too many requests. Please wait a minute and try again.",
                headers={"Retry-After": str(window)},
            )

    return dependency
