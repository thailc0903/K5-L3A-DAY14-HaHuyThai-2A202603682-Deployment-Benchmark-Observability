"""
Cost guard (tiêu chí 8).

Yêu cầu:
  • Cộng dồn chi phí LLM (tính theo token) vào Redis
  • Tổng chi phí vượt DAILY_BUDGET_USD (hoặc MONTHLY_BUDGET_USD) → HTTP 402
"""

# Giá USD / 1K tokens (tham khảo gpt-4o-mini)
PRICE_INPUT_PER_1K = 0.00015
PRICE_OUTPUT_PER_1K = 0.0006

import time

from fastapi import HTTPException

from app.config import settings
from app.redis_client import r


def _budget_key() -> str:
    return f"cost_guard:{time.strftime('%Y-%m-%d', time.gmtime())}"


def check_budget() -> None:
    """Gọi TRƯỚC khi gọi LLM. Hết budget → raise HTTPException(status_code=402)."""
    spent = float(r.get(_budget_key()) or 0.0)
    if spent >= settings.daily_budget_usd:
        raise HTTPException(status_code=402, detail="Daily budget exceeded")


def record_cost(input_tokens: int, output_tokens: int) -> float:
    """Gọi SAU khi gọi LLM. Cộng chi phí của request vào tổng, trả về chi phí request."""
    cost = (
        input_tokens / 1000 * PRICE_INPUT_PER_1K
        + output_tokens / 1000 * PRICE_OUTPUT_PER_1K
    )
    key = _budget_key()
    r.incrbyfloat(key, cost)
    r.expire(key, 2 * 24 * 60 * 60)
    return cost
