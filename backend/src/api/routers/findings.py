"""POST /api/findings/{id}/action endpoint."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from src.api.deps import get_finding_repository
from src.api.middleware.auth import get_current_user
from src.domain.models import UserAction
from src.domain.ports import IFindingRepository

router = APIRouter(prefix="/api/findings", tags=["findings"])


class FindingActionRequest(BaseModel):
    action: UserAction
    custom_fix: str | None = None


class FindingActionResponse(BaseModel):
    finding_id: uuid.UUID
    action: UserAction


@router.post("/{finding_id}/action", response_model=FindingActionResponse)
async def record_finding_action(
    finding_id: uuid.UUID,
    body: FindingActionRequest,
    user_id: uuid.UUID = Depends(get_current_user),
    finding_repo: IFindingRepository = Depends(get_finding_repository),
) -> FindingActionResponse:
    """Record a user action (accepted / ignored / custom) on a finding."""
    if body.action is UserAction.custom and not body.custom_fix:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="custom_fix is required when action is 'custom'",
        )

    await finding_repo.update_action(
        finding_id,
        body.action,
        custom_fix=body.custom_fix,
    )
    return FindingActionResponse(finding_id=finding_id, action=body.action)
