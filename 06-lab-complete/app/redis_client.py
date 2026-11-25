"""Redis client dùng chung; không kết nối mạng khi module được import."""
import redis
from redis.exceptions import RedisError

from app.config import settings


r = redis.from_url(
    settings.redis_url,
    decode_responses=True,
    socket_connect_timeout=1,
    socket_timeout=1,
)


def redis_healthy() -> bool:
    """Readiness phụ thuộc Redis, nhưng liveness không phụ thuộc Redis."""
    try:
        return bool(r.ping())
    except RedisError:
        return False
