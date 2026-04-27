"""GET /api/repos and POST /api/repos endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from src.api.deps import get_repo_repository
from src.api.middleware.auth import get_current_user
from src.domain.models import Repo
from src.domain.ports import IRepoRepository

router = APIRouter(prefix="/api/repos", tags=["repos"])


class ConnectRepoRequest(BaseModel):
    full_name: str  # "owner/repo"
    github_installation_id: int


@router.get("", response_model=list[Repo])
async def list_repos(
    user_id: uuid.UUID = Depends(get_current_user),
    repo_repo: IRepoRepository = Depends(get_repo_repository),
) -> list[Repo]:
    """Return all repos connected by the authenticated user."""
    return await repo_repo.get_by_user(user_id)


@router.post("", response_model=Repo, status_code=status.HTTP_201_CREATED)
async def connect_repo(
    body: ConnectRepoRequest,
    user_id: uuid.UUID = Depends(get_current_user),
    repo_repo: IRepoRepository = Depends(get_repo_repository),
) -> Repo:
    """Connect a new GitHub repo to the authenticated user's account."""
    existing = await repo_repo.get_by_installation(body.github_installation_id)
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A repo with this installation ID is already connected",
        )

    repo = Repo(
        user_id=user_id,
        full_name=body.full_name,
        github_installation_id=body.github_installation_id,
    )
    return await repo_repo.create(repo)
