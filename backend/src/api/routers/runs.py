"""GET /api/runs and GET /api/runs/{id} endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from src.api.deps import get_finding_repository, get_run_repository
from src.api.middleware.auth import get_current_user
from src.domain.models import AuditRun, Finding
from src.domain.ports import IFindingRepository, IRunRepository

router = APIRouter(prefix="/api/runs", tags=["runs"])


class RunListResponse(BaseModel):
    items: list[AuditRun]
    total: int
    page: int
    page_size: int


class RunDetailResponse(BaseModel):
    run: AuditRun
    findings: list[Finding]


@router.get("", response_model=RunListResponse)
async def list_runs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    user_id: uuid.UUID = Depends(get_current_user),
    run_repo: IRunRepository = Depends(get_run_repository),
) -> RunListResponse:
    """Return a paginated list of audit runs for the authenticated user."""
    runs, total = await run_repo.list_by_user(user_id, page=page, page_size=page_size)
    return RunListResponse(items=runs, total=total, page=page, page_size=page_size)


@router.get("/{run_id}", response_model=RunDetailResponse)
async def get_run(
    run_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user),
    run_repo: IRunRepository = Depends(get_run_repository),
    finding_repo: IFindingRepository = Depends(get_finding_repository),
) -> RunDetailResponse:
    """Return a single audit run and all its findings."""
    run = await run_repo.get_by_id(run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")

    findings = await finding_repo.get_by_run(run_id)
    return RunDetailResponse(run=run, findings=findings)
