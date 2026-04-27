from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.orm import AuditRunORM, RepoORM
from src.domain.exceptions import RepositoryError
from src.domain.models import AuditRun, AuditStatus
from src.domain.ports import IRunRepository


def _to_domain(row: AuditRunORM) -> AuditRun:
    return AuditRun(
        id=row.id,
        repo_id=row.repo_id,
        pr_number=row.pr_number,
        pr_title=row.pr_title or "",
        status=AuditStatus(row.status),
        finding_count=row.total_findings,
        drift_count=row.doc_drift_count,
        style_count=row.style_violation_count,
        cost_usd=float(row.cost_estimate_usd or 0),
        gh_comment_id=row.pr_comment_id,
        started_at=row.started_at or row.created_at,
        completed_at=row.finished_at,
        error=row.error_message,
    )


class RunRepository(IRunRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, run: AuditRun) -> AuditRun:
        try:
            repo_result = await self._session.execute(
                select(RepoORM).where(RepoORM.id == run.repo_id)
            )
            repo_row = repo_result.scalar_one_or_none()
            if repo_row is None:
                raise RepositoryError(f"Repo {run.repo_id} not found for run creation")

            row = AuditRunORM(
                id=run.id,
                repo_id=run.repo_id,
                user_id=repo_row.user_id,
                pr_number=run.pr_number,
                pr_title=run.pr_title,
                status=run.status.value,
                started_at=run.started_at,
            )
            self._session.add(row)
            await self._session.flush()
            return _to_domain(row)
        except Exception as exc:
            raise RepositoryError(f"Failed to create audit run: {exc}") from exc

    async def update_status(
        self,
        run_id: uuid.UUID,
        status: AuditStatus,
        *,
        error: str | None = None,
    ) -> None:
        try:
            result = await self._session.execute(
                select(AuditRunORM).where(AuditRunORM.id == run_id)
            )
            row = result.scalar_one_or_none()
            if row is None:
                raise RepositoryError(f"AuditRun {run_id} not found")
            row.status = status.value
            if error:
                row.error_message = error
            if status in (AuditStatus.completed, AuditStatus.failed):
                row.finished_at = datetime.utcnow()
            await self._session.flush()
        except RepositoryError:
            raise
        except Exception as exc:
            raise RepositoryError(f"Failed to update run status: {exc}") from exc

    async def finalize_run(
        self,
        run_id: uuid.UUID,
        *,
        status: AuditStatus,
        finding_count: int,
        drift_count: int,
        style_count: int,
        cost_usd: float,
        duration_ms: int,
        comment_id: int | None = None,
        error: str | None = None,
    ) -> None:
        try:
            result = await self._session.execute(
                select(AuditRunORM).where(AuditRunORM.id == run_id)
            )
            row = result.scalar_one_or_none()
            if row is None:
                raise RepositoryError(f"AuditRun {run_id} not found")
            row.status = status.value
            row.total_findings = finding_count
            row.doc_drift_count = drift_count
            row.style_violation_count = style_count
            row.cost_estimate_usd = cost_usd
            row.duration_ms = duration_ms
            row.finished_at = datetime.utcnow()
            if comment_id is not None:
                row.pr_comment_id = comment_id
            if error:
                row.error_message = error
            await self._session.flush()
        except RepositoryError:
            raise
        except Exception as exc:
            raise RepositoryError(f"Failed to finalize run {run_id}: {exc}") from exc

    async def get_by_id(self, run_id: uuid.UUID) -> AuditRun | None:
        try:
            result = await self._session.execute(
                select(AuditRunORM).where(AuditRunORM.id == run_id)
            )
            row = result.scalar_one_or_none()
            return _to_domain(row) if row else None
        except Exception as exc:
            raise RepositoryError(f"Failed to fetch run {run_id}: {exc}") from exc

    async def list_by_repo(self, repo_id: uuid.UUID) -> list[AuditRun]:
        try:
            result = await self._session.execute(
                select(AuditRunORM)
                .where(AuditRunORM.repo_id == repo_id)
                .order_by(AuditRunORM.created_at.desc())
            )
            return [_to_domain(r) for r in result.scalars().all()]
        except Exception as exc:
            raise RepositoryError(f"Failed to list runs for repo {repo_id}: {exc}") from exc

    async def list_by_user(
        self, user_id: uuid.UUID, *, page: int = 1, page_size: int = 20
    ) -> tuple[list[AuditRun], int]:
        try:
            base_query = (
                select(AuditRunORM)
                .join(RepoORM, AuditRunORM.repo_id == RepoORM.id)
                .where(RepoORM.user_id == user_id)
            )
            count_result = await self._session.execute(
                select(func.count()).select_from(base_query.subquery())
            )
            total = count_result.scalar_one()
            offset = (page - 1) * page_size
            rows_result = await self._session.execute(
                base_query.order_by(AuditRunORM.created_at.desc())
                .offset(offset)
                .limit(page_size)
            )
            return [_to_domain(r) for r in rows_result.scalars().all()], total
        except Exception as exc:
            raise RepositoryError(
                f"Failed to list runs for user {user_id}: {exc}"
            ) from exc
