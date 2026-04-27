import asyncio
import contextlib
import logging
from collections.abc import AsyncGenerator
from typing import Any

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


# Lambda handler: dual-routing between HTTP (API Gateway) and direct invocations.
# When AUDIT_DISPATCH_MODE=lambda_async, the webhook handler invokes this same Lambda
# with the AuditDispatchEvent payload directly (InvocationType="Event").  Mangum only
# understands HTTP events, so we detect the direct-invocation shape and route it to
# run_background_audit instead.
_mangum = Mangum(app, lifespan="off")


def handler(event: dict[str, Any], context: Any) -> Any:
    if "run_id" in event and "installation_id" in event:
        # Direct Lambda invocation — run the audit pipeline.
        from src.services.audit_background_runner import run_background_audit
        from src.services.audit_dispatcher import AuditDispatchEvent

        audit_event = AuditDispatchEvent(**event)
        # Use new_event_loop + set_event_loop rather than asyncio.run().
        # asyncio.run() closes the loop after completion; on a warm Lambda
        # reuse the next call (HTTP) hits Mangum which calls get_event_loop()
        # and crashes because the loop was torn down.
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(run_background_audit(audit_event))
        return {"status": "ok"}

    # API Gateway / ALB event — let Mangum handle it as HTTP.
    return _mangum(event, context)
