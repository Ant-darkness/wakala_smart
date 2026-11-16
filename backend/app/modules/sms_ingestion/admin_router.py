from typing import Annotated
from uuid import UUID

from app.db.session import get_db
from app.models.transaction_enums import TransactionNetwork
from app.modules.auth.dependencies import get_current_platform_user
from app.modules.sms_ingestion.admin_schemas import (
    SmsPatternCreateRequest,
    SmsPatternResponse,
)
from app.modules.sms_ingestion.admin_service import (
    create_sms_pattern,
    list_sms_patterns,
    set_sms_pattern_active,
)
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

router = APIRouter(
    prefix="/platform/admin/sms-patterns",
    tags=["Platform SMS Parser Management"],
)


@router.post(
    "",
    response_model=SmsPatternResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_pattern(
    payload: SmsPatternCreateRequest,
    db: Session = Depends(get_db),
    admin=Depends(get_current_platform_user),
):
    try:
        return create_sms_pattern(
            db,
            admin_id=admin.id,
            network=payload.network,
            name=payload.name,
            description=payload.description,
            pattern=payload.pattern,
            version=payload.version,
            priority=payload.priority,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc


@router.get(
    "",
    response_model=list[SmsPatternResponse],
)
def get_patterns(
    network: Annotated[
        TransactionNetwork | None,
        Query(),
    ] = None,
    db: Session = Depends(get_db),
    admin=Depends(get_current_platform_user),
):
    return list_sms_patterns(
        db,
        network=network,
    )


@router.patch(
    "/{pattern_id}/activate",
    response_model=SmsPatternResponse,
)
def activate_pattern(
    pattern_id: UUID,
    db: Session = Depends(get_db),
    admin=Depends(get_current_platform_user),
):
    try:
        return set_sms_pattern_active(
            db,
            admin_id=admin.id,
            pattern_id=pattern_id,
            is_active=True,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.patch(
    "/{pattern_id}/deactivate",
    response_model=SmsPatternResponse,
)
def deactivate_pattern(
    pattern_id: UUID,
    db: Session = Depends(get_db),
    admin=Depends(get_current_platform_user),
):
    try:
        return set_sms_pattern_active(
            db,
            admin_id=admin.id,
            pattern_id=pattern_id,
            is_active=False,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
