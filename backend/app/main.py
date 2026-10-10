from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api.routes.datasets import router as datasets_router
from app.api.routes.investigations import router as investigations_router
from app.core.config import get_settings
from app.core.database import SessionLocal

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Startup validation: verify provider configuration
    if settings.llm_provider and settings.llm_provider.strip().lower() == "gemini":
        if not settings.google_api_key or not settings.google_api_key.strip():
            raise RuntimeError(
                "GOOGLE_API_KEY is required when LLM_PROVIDER is configured to 'gemini'."
            )
    yield


app = FastAPI(
    title=settings.app_name,
    description="Autonomous data quality and investigation platform",
    version="0.1.0",
    lifespan=lifespan,
)

allowed_origins = [
    settings.frontend_origin,
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
@app.get("/api/v1/health")
def health_check() -> dict:
    postgres_ok = True
    redis_ok = True
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
    except Exception:
        postgres_ok = False
    try:
        import redis

        client = redis.Redis.from_url(settings.redis_url, decode_responses=True, socket_timeout=2)
        redis_ok = bool(client.ping())
    except Exception:
        redis_ok = False

    payload = {
        "status": "ok" if postgres_ok and redis_ok else "degraded",
        "service": settings.app_name,
        "environment": settings.app_env,
        "postgres": "ok" if postgres_ok else "down",
        "redis": "ok" if redis_ok else "down",
    }
    if not (postgres_ok and redis_ok):
        raise HTTPException(status_code=503, detail=payload)
    return payload


app.include_router(datasets_router)
app.include_router(investigations_router)
