import structlog
from fastapi import FastAPI
from mangum import Mangum

from src.api.routers import webhooks
from src.config import settings

structlog.configure(
    wrapper_class=structlog.make_filtering_bound_logger(
        __import__("logging").getLevelName(settings.log_level)
    ),
)

app = FastAPI(
    title="DocGuard API",
    description="AI-powered GitHub PR reviewer — doc drift + style violations",
    version="0.1.0",
    docs_url="/docs" if settings.environment != "production" else None,
)

app.include_router(webhooks.router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "environment": settings.environment}


# Lambda handler (Mangum wraps the ASGI app)
handler = Mangum(app, lifespan="off")
