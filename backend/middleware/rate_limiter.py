"""
Module: middleware/rate_limiter.py
Purpose: Redis sliding-window per-identity rate limiting (ASGI middleware).
         Limits each client to `settings.rate_limit_per_min` requests per 60s
         using a Redis sorted-set. Fails open on Redis connection errors so that
         a Redis outage never cascades into HTTP 500s for all requests.
Dependencies: redis, starlette
Author: ApplyPilot
"""
import time

import redis
from jose import JWTError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from config import settings
from deps import get_redis
from security.jwt import decode_token
from utils.logger import get_logger

logger = get_logger(__name__)

LIMIT: int = settings.rate_limit_per_min
WINDOW_SEC: int = 60
EXEMPT: set[str] = {"/health"}


def _redis() -> redis.Redis:
    """Return a Redis client (indirection point for tests).

    Returns:
        A Redis client from the shared connection pool.
    """
    return get_redis()


def _identity(request: Request) -> str:
    """Derive a rate-limit key from the JWT ``sub`` claim or client IP.

    Decodes the Bearer token and keys on the ``sub`` claim so that each
    authenticated user gets a separate rate-limit bucket. Falls back to
    the IP-based identity if the token is absent or cannot be decoded
    (fail-safe: a decode failure never blocks the request here).

    Args:
        request: The incoming Starlette request.

    Returns:
        A string key identifying this client, e.g. ``user:<uuid>`` for an
        authenticated request or ``ip:127.0.0.1`` for an unauthenticated one.
    """
    auth = request.headers.get("authorization", "")
    if auth.startswith("Bearer "):
        try:
            claims = decode_token(auth[7:])
            sub = claims.get("sub")
            if sub:
                return f"user:{sub}"
        except JWTError:
            pass  # fall through to IP-based identity
    return f"ip:{request.client.host if request.client else 'unknown'}"


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Sliding-window rate limiter using a Redis sorted set per client identity.

    Each request increments a sorted set keyed by client identity. Members
    older than WINDOW_SEC are pruned on every request. If the member count
    exceeds LIMIT the request is rejected with HTTP 429 and a ``Retry-After``
    header.

    On Redis connection errors (``redis.RedisError``) the middleware logs a
    warning and fails open — the request is allowed through so that a Redis
    outage does not break the API.
    """

    async def dispatch(self, request: Request, call_next) -> Response:  # type: ignore[override]
        """Apply sliding-window rate limiting to the request.

        Passes through exempt paths and requests when Redis is unavailable.
        Returns 429 JSON with ``Retry-After`` header when the limit is exceeded.

        Args:
            request: The incoming HTTP request.
            call_next: ASGI callable for the next middleware/handler.

        Returns:
            The response from the next handler, or a 429 JSONResponse when the
            rate limit is exceeded.
        """
        if request.method == "OPTIONS":
            return await call_next(request)
        if request.url.path in EXEMPT:
            return await call_next(request)

        client = _redis()
        key = f"rl:{_identity(request)}"
        now = time.time()

        try:
            pipe = client.pipeline()
            pipe.zremrangebyscore(key, 0, now - WINDOW_SEC)
            pipe.zadd(key, {str(now): now})
            pipe.zcard(key)
            pipe.expire(key, WINDOW_SEC)
            results = pipe.execute()
            count: int = results[2]
        except redis.RedisError as exc:
            logger.warning(
                "Rate limiter Redis error — failing open: %s", exc
            )
            return await call_next(request)

        if count > LIMIT:
            return JSONResponse(
                {"detail": "Rate limit exceeded"},
                status_code=429,
                headers={"Retry-After": str(WINDOW_SEC)},
            )
        return await call_next(request)
