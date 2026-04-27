from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from typing import Any

import structlog
from fastapi import BackgroundTasks

from src.config import settings
from src.domain.exceptions import AuditRunError

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class AuditDispatchEvent:
    run_id: str
    installation_id: int
    repo_full_name: str
    pr_number: int
    head_sha: str
    action: str

    @classmethod
    def from_webhook_payload(cls, payload: dict[str, Any], run_id: uuid.UUID) -> AuditDispatchEvent:
        installation_id = payload.get("installation", {}).get("id")
        repo_full_name = payload.get("repository", {}).get("full_name")
        pr_number = payload.get("number")
        head_sha = payload.get("pull_request", {}).get("head", {}).get("sha")
        action = payload.get("action", "")

        if installation_id is None:
            raise AuditRunError("Webhook payload missing installation.id", run_id=str(run_id))
        if not repo_full_name:
            raise AuditRunError("Webhook payload missing repository.full_name", run_id=str(run_id))
        if pr_number is None:
            raise AuditRunError("Webhook payload missing pull request number", run_id=str(run_id))
        if not head_sha:
            raise AuditRunError("Webhook payload missing pull_request.head.sha", run_id=str(run_id))

        return cls(
            run_id=str(run_id),
            installation_id=int(installation_id),
            repo_full_name=str(repo_full_name),
            pr_number=int(pr_number),
            head_sha=str(head_sha),
            action=str(action),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "installation_id": self.installation_id,
            "repo_full_name": self.repo_full_name,
            "pr_number": self.pr_number,
            "head_sha": self.head_sha,
            "action": self.action,
        }


class AuditDispatcher:
    """Dispatches webhook-triggered audits according to environment strategy."""

    async def dispatch(self, event: AuditDispatchEvent, background_tasks: BackgroundTasks) -> None:
        mode = settings.audit_dispatch_mode.strip().lower()
        if mode == "background":
            # Lazy import avoids circular import with audit_background_runner.
            from src.services.audit_background_runner import run_background_audit

            background_tasks.add_task(run_background_audit, event)
            return
        if mode == "lambda_async":
            self._dispatch_lambda_async(event)
            return
        if mode == "sqs":
            self._dispatch_sqs(event)
            return
        raise AuditRunError(
            f"Unsupported AUDIT_DISPATCH_MODE='{settings.audit_dispatch_mode}'", run_id=event.run_id
        )

    def _dispatch_lambda_async(self, event: AuditDispatchEvent) -> None:
        if not settings.audit_worker_lambda_name:
            raise AuditRunError(
                "AUDIT_WORKER_LAMBDA_NAME is required for lambda_async mode", run_id=event.run_id
            )

        try:
            import boto3
        except Exception as exc:  # pragma: no cover
            raise AuditRunError(
                "boto3 is required for lambda_async dispatch mode", run_id=event.run_id
            ) from exc

        client = boto3.client("lambda", region_name=settings.aws_region)
        response = client.invoke(
            FunctionName=settings.audit_worker_lambda_name,
            InvocationType="Event",
            Payload=json.dumps(event.to_dict()).encode("utf-8"),
        )
        status_code = int(response.get("StatusCode", 0))
        if status_code != 202:
            raise AuditRunError(
                f"Lambda async invoke failed with StatusCode={status_code}", run_id=event.run_id
            )

        logger.info("audit.dispatch.lambda_async", **event.to_dict(), lambda_status_code=status_code)

    def _dispatch_sqs(self, event: AuditDispatchEvent) -> None:
        if not settings.audit_sqs_queue_url:
            raise AuditRunError("AUDIT_SQS_QUEUE_URL is required for sqs mode", run_id=event.run_id)

        try:
            import boto3
        except Exception as exc:  # pragma: no cover
            raise AuditRunError("boto3 is required for sqs dispatch mode", run_id=event.run_id) from exc

        client = boto3.client("sqs", region_name=settings.aws_region)
        response = client.send_message(
            QueueUrl=settings.audit_sqs_queue_url,
            MessageBody=json.dumps(event.to_dict()),
        )
        logger.info(
            "audit.dispatch.sqs",
            **event.to_dict(),
            message_id=response.get("MessageId"),
        )
