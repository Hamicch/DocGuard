from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.orm import FindingORM
from src.domain.exceptions import RepositoryError
from src.domain.models import Finding, FindingType, Severity, UserAction
from src.domain.ports import IFindingRepository


def _to_domain(row: FindingORM) -> Finding:
    return Finding(
        id=row.id,
        run_id=row.run_id,
        finding_type=FindingType(row.finding_type),
        severity=Severity(row.severity),
        file_path=row.file_path,
        line_start=row.line_number,
        title=row.title,
        description=row.description or "",
        proposed_fix=row.proposed_fix,
        user_action=UserAction(row.user_action) if row.user_action else UserAction.pending,
        created_at=row.created_at,
    )


class FindingRepository(IFindingRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def bulk_create(self, findings: list[Finding]) -> list[Finding]:
        try:
            rows = [
                FindingORM(
                    id=f.id,
                    run_id=f.run_id,
                    finding_type=f.finding_type.value,
                    severity=f.severity.value,
                    file_path=f.file_path,
                    line_number=f.line_start,
                    title=f.title,
                    description=f.description,
                    proposed_fix=f.proposed_fix,
                    user_action=f.user_action.value,
                )
                for f in findings
            ]
            self._session.add_all(rows)
            await self._session.flush()
            return [_to_domain(r) for r in rows]
        except Exception as exc:
            raise RepositoryError(f"Failed to bulk-create findings: {exc}") from exc

    async def get_by_run(self, run_id: uuid.UUID) -> list[Finding]:
        try:
            result = await self._session.execute(
                select(FindingORM)
                .where(FindingORM.run_id == run_id)
                .order_by(FindingORM.severity, FindingORM.created_at)
            )
            return [_to_domain(r) for r in result.scalars().all()]
        except Exception as exc:
            raise RepositoryError(f"Failed to fetch findings for run {run_id}: {exc}") from exc

    async def update_action(self, finding_id: uuid.UUID, action: UserAction) -> None:
        try:
            result = await self._session.execute(
                select(FindingORM).where(FindingORM.id == finding_id)
            )
            row = result.scalar_one_or_none()
            if row is None:
                raise RepositoryError(f"Finding {finding_id} not found")
            row.user_action = action.value
            await self._session.flush()
        except RepositoryError:
            raise
        except Exception as exc:
            raise RepositoryError(f"Failed to update finding action: {exc}") from exc
