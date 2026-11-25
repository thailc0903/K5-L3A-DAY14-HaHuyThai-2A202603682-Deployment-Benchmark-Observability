"""
Rate limiting (tiêu chí 7).

Yêu cầu:
  • Mỗi API key tối đa RATE_LIMIT_PER_MINUTE request trong 60 giây (sliding window)
  • Vượt giới hạn → HTTP 429, nên kèm header Retry-After
  • State lưu trong Redis để mọi worker / instance dùng chung và vẫn còn sau khi
    restart agent (script chấm sẽ restart agent để kiểm tra)
"""
import hashlib
import time
import uuid

from fastapi import HTTPException

from app.config import settings
from app.redis_client import r


def check_rate_limit(key: str) -> None:
    """Sliding-window limit, với state dùng chung giữa mọi worker qua Redis."""
    now = time.time()
    window_seconds = 60
    redis_key = "rate_limit:" + hashlib.sha256(key.encode()).hexdigest()

    # Xóa timestamp ngoài cửa sổ rồi đếm request còn hiệu lực.
    r.zremrangebyscore(redis_key, "-inf", now - window_seconds)
    count = r.zcard(redis_key)
    if count >= settings.rate_limit_per_minute:
        oldest = r.zrange(redis_key, 0, 0, withscores=True)
        retry_after = 1
        if oldest:
            retry_after = max(1, int(oldest[0][1] + window_seconds - now) + 1)
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded",
            headers={"Retry-After": str(retry_after)},
        )

    # Member phải unique vì nhiều request có thể cùng timestamp.
    r.zadd(redis_key, {f"{now}:{uuid.uuid4().hex}": now})
    r.expire(redis_key, window_seconds + 1)
