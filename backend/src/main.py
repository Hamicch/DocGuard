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


# ── Lambda entry point ────────────────────────────────────────────────────────
#
# The same function handles two distinct invocation patterns:
#
#   1. API Gateway proxy event  →  Mangum → FastAPI (webhooks, REST API)
#   2. Direct async invocation  →  audit pipeline runner
#      (triggered by AuditDispatcher in lambda_async mode)
#
# A direct audit event is identified by the presence of the "run_id" key,
# which is never present in APIGW proxy events.

_mangum = Mangum(app, lifespan="off")


def handler(event: dict, context: object) -> dict:  # type: ignore[type-arg]
    if "run_id" in event:
        # Direct Lambda invocation — run the audit pipeline synchronously.
        import asyncio

        from src.services.audit_background_runner import run_background_audit
        from src.services.audit_dispatcher import AuditDispatchEvent

        log = structlog.get_logger(__name__)
        log.info("lambda.audit_dispatch.received", run_id=event.get("run_id"))
        dispatch_event = AuditDispatchEvent(
            run_id=str(event["run_id"]),
            installation_id=int(event["installation_id"]),
            repo_full_name=str(event["repo_full_name"]),
            pr_number=int(event["pr_number"]),
            head_sha=str(event["head_sha"]),
            action=str(event.get("action", "")),
        )
        asyncio.run(run_background_audit(dispatch_event))
        return {"statusCode": 200, "body": "audit complete"}

    # Standard API Gateway / function URL invocation.
    return _mangum(event, context)  # type: ignore[arg-type]
