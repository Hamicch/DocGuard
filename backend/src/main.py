import contextlib
import logging
from collections.abc import AsyncGenerator

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum

from src.api.routers import findings, repos, runs, webhooks
from src.config import settings
from src.db.engine import engine

structlog.configure(
    wrapper_class=structlog.make_filtering_bound_logger(
        logging.getLevelName(settings.log_level)
    ),
)


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    yield
    await engine.dispose()


app = FastAPI(
    title="DocGuard API",
    description="AI-powered GitHub PR reviewer — doc drift + style violations",
    version="0.1.0",
    docs_url="/docs" if settings.environment != "production" else None,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.environment != "production" else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(webhooks.router)
app.include_router(runs.router)
app.include_router(findings.router)
app.include_router(repos.router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "environment": settings.environment}


# Lambda handler (Mangum wraps the ASGI app)
handler = Mangum(app, lifespan="off")
