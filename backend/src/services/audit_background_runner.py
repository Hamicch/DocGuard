"""Run the audit pipeline from FastAPI ``BackgroundTasks`` (local / single-Lambda).

When ``AUDIT_DISPATCH_MODE=background``, the webhook handler schedules this
coroutine. It creates the ``audit_runs`` row immediately so the dashboard can
list the run, then executes ``AuditOrchestrator.run_audit`` on the same DB
session.
"""

from __future__ import annotations

import uuid

import structlog

from src.adapters.github import GitHubAdapter
from src.adapters.llm_client import LLMClient
from src.db.engine import AsyncSessionFactory
from src.domain.models import AuditRun, AuditStatus
from src.repositories.finding_repository import FindingRepository
from src.repositories.repo_repository import RepoRepository
from src.repositories.run_repository import RunRepository
from src.services.audit_dispatcher import AuditDispatchEvent
from src.services.audit_orchestrator import AuditOrchestrator

logger = structlog.get_logger(__name__)


async def run_background_audit(event: AuditDispatchEvent) -> None:
    """Look up the connected repo, persist a pending run, then run the pipeline."""
    run_uuid = uuid.UUID(event.run_id)
    log = logger.bind(
        run_id=event.run_id,
        pr=event.pr_number,
        repo=event.repo_full_name,
        installation_id=event.installation_id,
    )

    async with AsyncSessionFactory() as session:
        repo_repo = RepoRepository(session)
        run_repo = RunRepository(session)
        finding_repo = FindingRepository(session)

        try:
            repo = await repo_repo.get_by_installation(event.installation_id)
            if repo is None:
                log.warning(
                    "audit.skip_repo_not_connected",
                    detail="No repos row for this installation; connect the repo in Settings",
                )
                return
            if repo.full_name != event.repo_full_name:
                log.warning(
                    "audit.skip_repo_mismatch",
                    expected_full_name=event.repo_full_name,
                    connected_full_name=repo.full_name,
                )
                return

            pending = AuditRun(
                id=run_uuid,
                repo_id=repo.id,
                pr_number=event.pr_number,
                pr_title=event.pr_title,
                status=AuditStatus.pending,
            )
            await run_repo.create(pending)
            await session.commit()

            github = GitHubAdapter()
            llm = LLMClient.from_settings()
            orch = AuditOrchestrator(github, llm, run_repo, finding_repo)

            await orch.run_audit(
                pending,
                event.repo_full_name,
                event.installation_id,
                event.head_sha,
            )
            await session.commit()
        except Exception:
            await session.rollback()
            log.exception(
                "audit.background_failed",
                detail=(
                    "Exception swallowed so the webhook request can finish successfully "
                    "(GitHub otherwise sees HTTP 500). Inspect logs and DB for run state."
                ),
            )
            # Do not re-raise: BackgroundTasks run after the response is sent; an
            # uncaught exception here still fails the ASGI cycle and API Gateway
            # returns 500 to GitHub despite the route returning 202 Accepted.
