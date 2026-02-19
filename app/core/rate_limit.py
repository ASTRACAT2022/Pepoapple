import time
from collections import defaultdict, deque
from typing import Optional

import redis
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.core.config import get_settings

settings = get_settings()


class InMemoryRateStore:
    def __init__(self) -> None:
        self._buckets: dict[str, deque[float]] = defaultdict(deque)

    def hit(self, key: str, limit: int, window_seconds: int) -> bool:
        now = time.time()
        bucket = self._buckets[key]
        threshold = now - window_seconds
        while bucket and bucket[0] < threshold:
            bucket.popleft()
        if len(bucket) >= limit:
            return False
        bucket.append(now)
        return True


class RateLimiter:
    def __init__(self, redis_url: str, limit_per_minute: int) -> None:
        self.limit_per_minute = limit_per_minute
        self.redis_client: Optional[redis.Redis] = None
        self.memory_store = InMemoryRateStore()
        try:
            self.redis_client = redis.from_url(redis_url, decode_responses=True)
            self.redis_client.ping()
        except Exception:
            self.redis_client = None

    def allow(self, key: str) -> bool:
        if self.redis_client is not None:
            redis_key = f"rl:{key}:{int(time.time() // 60)}"
            current = self.redis_client.incr(redis_key)
            if current == 1:
                self.redis_client.expire(redis_key, 60)
            return current <= self.limit_per_minute
        return self.memory_store.hit(key, self.limit_per_minute, 60)


rate_limiter = RateLimiter(settings.redis_url, settings.rate_limit_per_minute)


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path in {"/health", "/api/v1/health"}:
            return await call_next(request)

        client_host = request.client.host if request.client else "unknown"
        auth_marker = request.headers.get("authorization") or request.headers.get("x-api-key") or client_host
        key = f"{client_host}:{request.url.path}:{hash(auth_marker)}"
        if not rate_limiter.allow(key):
            return JSONResponse(status_code=429, content={"error": "rate_limit_exceeded"})

        return await call_next(request)
