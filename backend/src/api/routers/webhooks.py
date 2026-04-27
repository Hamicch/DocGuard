from __future__ import annotations

import hashlib
import hmac
import json
import uuid
from typing import Any

import structlog
from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Request, status

from src.config import settings
from src.domain.exceptions import AuditRunError, WebhookVerificationError
from src.services.audit_dispatcher import AuditDispatcher, AuditDispatchEvent

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

SUPPORTED_ACTIONS = {"opened", "synchronize", "reopened"}
dispatcher = AuditDispatcher()


def _verify_signature(body: bytes, signature_header: str | None) -> None:
    """Raise WebhookVerificationError if the HMAC-SHA256 signature does not match."""
    if not signature_header:
        raise WebhookVerificationError("Missing X-Hub-Signature-256 header")

    if not signature_header.startswith("sha256="):
        raise WebhookVerificationError("Malformed X-Hub-Signature-256 header")

    expected = hmac.new(
        settings.github_webhook_secret.encode(),
        body,
        hashlib.sha256,
    ).hexdigest()
    received = signature_header.removeprefix("sha256=")

    if not hmac.compare_digest(expected, received):
        raise WebhookVerificationError("Signature mismatch")


@router.post(
    "/github",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Receive GitHub App webhook events",
)
async def github_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_hub_signature_256: str | None = Header(default=None),
    x_github_event: str | None = Header(default=None),
) -> dict[str, str]:
    body = await request.body()

    try:
        _verify_signature(body, x_hub_signature_256)
    except WebhookVerificationError as exc:
        logger.warning("webhook.signature_invalid", detail=str(exc))
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    if x_github_event != "pull_request":
        logger.debug("webhook.event_skipped", github_event=x_github_event)
        return {"status": "skipped", "reason": f"event '{x_github_event}' not handled"}

    try:
        payload: dict[str, Any] = json.loads(body)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON payload"
        ) from exc

    action = payload.get("action", "")
    if action not in SUPPORTED_ACTIONS:
        logger.debug("webhook.action_skipped", action=action)
        return {"status": "skipped", "reason": f"action '{action}' not handled"}

    run_id = uuid.uuid4()
    pr_number = payload.get("number")
    repo_full_name = payload.get("repository", {}).get("full_name", "unknown")

    logger.info(
        "webhook.pull_request.accepted",
        run_id=str(run_id),
        repo=repo_full_name,
        pr=pr_number,
        action=action,
    )

    try:
        event = AuditDispatchEvent.from_webhook_payload(payload, run_id)
        await dispatcher.dispatch(event, background_tasks)
    except AuditRunError as exc:
        logger.error("webhook.dispatch_failed", run_id=str(run_id), error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Audit dispatch failed",
        ) from exc

    return {"status": "triggered", "run_id": str(run_id)}
