from __future__ import annotations

import asyncio
import logging
import time
from collections import defaultdict, deque
from typing import Deque, Dict

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from settings import get_settings

logger = logging.getLogger("miji.api")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        started = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = round((time.perf_counter() - started) * 1000.0, 2)
        logger.info("%s %s -> %s in %sms", request.method, request.url.path, response.status_code, elapsed_ms)
        response.headers["X-Response-Time-Ms"] = str(elapsed_ms)
        return response


class TimeoutMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        timeout = get_settings().request_timeout_seconds
        try:
            return await asyncio.wait_for(call_next(request), timeout=timeout)
        except asyncio.TimeoutError:
            return JSONResponse(
                status_code=504,
                content={
                    "detail": "Request timed out",
                    "path": request.url.path,
                    "timeout_seconds": timeout,
                },
            )


class RateLimitMiddleware(BaseHTTPMiddleware):
    _buckets: Dict[str, Deque[float]] = defaultdict(deque)

    async def dispatch(self, request: Request, call_next):
        settings = get_settings()
        now = time.time()
        client = request.client.host if request.client else "unknown"
        bucket = self._buckets[client]

        while bucket and now - bucket[0] > settings.rate_limit_window_seconds:
            bucket.popleft()

        if len(bucket) >= settings.rate_limit_requests:
            retry_after = max(1, int(settings.rate_limit_window_seconds - (now - bucket[0])))
            return JSONResponse(
                status_code=429,
                headers={"Retry-After": str(retry_after)},
                content={
                    "detail": "Too many requests",
                    "retry_after_seconds": retry_after,
                },
            )

        bucket.append(now)
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(settings.rate_limit_requests)
        response.headers["X-RateLimit-Remaining"] = str(max(0, settings.rate_limit_requests - len(bucket)))
        return response
