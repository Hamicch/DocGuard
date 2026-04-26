from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.orm import RepoORM
from src.domain.exceptions import RepositoryError
from src.domain.models import Repo
from src.domain.ports import IRepoRepository


def _to_domain(row: RepoORM) -> Repo:
    return Repo(
        id=row.id,
        user_id=row.user_id,
        full_name=row.full_name,
        github_installation_id=row.github_installation_id or 0,
        created_at=row.created_at,
    )


class RepoRepository(IRepoRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, repo: Repo) -> Repo:
        try:
            row = RepoORM(
                id=repo.id,
                user_id=repo.user_id,
                full_name=repo.full_name,
                github_installation_id=repo.github_installation_id,
            )
            self._session.add(row)
            await self._session.flush()
            return _to_domain(row)
        except Exception as exc:
            raise RepositoryError(f"Failed to create repo: {exc}") from exc

    async def get_by_user(self, user_id: uuid.UUID) -> list[Repo]:
        try:
            result = await self._session.execute(
                select(RepoORM).where(RepoORM.user_id == user_id, RepoORM.is_active.is_(True))
            )
            return [_to_domain(r) for r in result.scalars().all()]
        except Exception as exc:
            raise RepositoryError(f"Failed to fetch repos for user {user_id}: {exc}") from exc

    async def get_by_installation(self, installation_id: int) -> Repo | None:
        try:
            result = await self._session.execute(
                select(RepoORM).where(RepoORM.github_installation_id == installation_id)
            )
            row = result.scalar_one_or_none()
            return _to_domain(row) if row else None
        except Exception as exc:
            raise RepositoryError(
                f"Failed to fetch repo for installation {installation_id}: {exc}"
            ) from exc
