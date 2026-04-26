from fastapi import FastAPI
from mangum import Mangum

from src.config import settings

app = FastAPI(
    title="DocGuard API",
    description="AI-powered GitHub PR reviewer — doc drift + style violations",
    version="0.1.0",
    docs_url="/docs" if settings.environment != "production" else None,
)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "environment": settings.environment}


# Lambda handler (Mangum wraps the ASGI app)
handler = Mangum(app, lifespan="off")
