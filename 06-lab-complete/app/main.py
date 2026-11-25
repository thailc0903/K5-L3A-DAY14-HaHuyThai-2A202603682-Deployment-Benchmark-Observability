"""
Production AI Agent — Part 6 Final Project (bản khung)

Hoàn thành các TODO để đạt đủ 12 tiêu chí trong README.md, rồi kiểm tra:
    python check_production_ready.py

Bản khung này chạy được (uvicorn app.main:app) nhưng chưa đạt tiêu chí nào.
"""
import json
import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field

from app.config import settings
from app.auth import verify_api_key
from app.cost_guard import check_budget, record_cost
from app.rate_limiter import check_rate_limit
from app.redis_client import redis_healthy
from utils.mock_llm import ask as llm_ask

class JsonFormatter(logging.Formatter):
    """Mỗi log của application là một JSON object trên một dòng."""

    def format(self, record: logging.LogRecord) -> str:
        return json.dumps(
            {
                "ts": datetime.now(timezone.utc).isoformat(),
                "level": record.levelname,
                "event": record.getMessage(),
            },
            ensure_ascii=False,
        )


logger = logging.getLogger("production_agent")
logger.setLevel(logging.INFO)
logger.propagate = False
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)

START_TIME = time.time()

@asynccontextmanager
async def lifespan(_: FastAPI):
    logger.info("startup")
    yield
    logger.info("shutdown")


app = FastAPI(title="Production AI Agent", lifespan=lifespan)


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)


@app.get("/health")
def health():
    """Liveness: chỉ cần process còn chạy, Redis down vẫn phải trả 200."""
    return {
        "status": "ok",
        "uptime_seconds": round(time.time() - START_TIME, 3),
        "environment": settings.environment,
    }


@app.get("/ready")
def ready():
    """Readiness: không nhận traffic nếu dependency Redis không sẵn sàng."""
    if not redis_healthy():
        raise HTTPException(status_code=503, detail="Redis is not ready")
    return {"status": "ready"}


@app.post("/ask")
def ask(body: AskRequest, api_key: str = Depends(verify_api_key)):
    check_rate_limit(api_key)
    check_budget()
    answer = llm_ask(body.question)
    request_cost = record_cost(
        input_tokens=len(body.question.split()),
        output_tokens=len(answer.split()),
    )
    logger.info("ask_completed")
    return {"question": body.question, "answer": answer, "cost_usd": request_cost}


# Uvicorn nhận SIGTERM và thực hiện lifespan shutdown; không ghi đè signal handler của Uvicorn.
