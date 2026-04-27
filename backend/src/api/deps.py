"""Shared FastAPI dependencies for the API layer."""

from __future__ import annotations

from collections.abc import AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.engine import get_session
from src.domain.ports import IFindingRepository, IRepoRepository, IRunRepository
from src.repositories.finding_repository import FindingRepository
from src.repositories.repo_repository import RepoRepository
from src.repositories.run_repository import RunRepository


async def get_run_repository(
    session: AsyncSession = Depends(get_session),
) -> AsyncGenerator[IRunRepository, None]:
    yield RunRepository(session)


async def get_finding_repository(
    session: AsyncSession = Depends(get_session),
) -> AsyncGenerator[IFindingRepository, None]:
    yield FindingRepository(session)


async def get_repo_repository(
    session: AsyncSession = Depends(get_session),
) -> AsyncGenerator[IRepoRepository, None]:
    yield RepoRepository(session)
