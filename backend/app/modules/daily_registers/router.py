from uuid import UUID

from app.db.session import get_db
from app.models.daily_register_balance import DailyRegisterBalance
from app.modules.daily_registers.schemas import (
    DailyRegisterDetailResponse,
    DailyRegisterListResponse,
    DailyRegisterOpenRequest,
    DailyRegisterResponse,
)
from app.modules.daily_registers.service import (
    close_daily_register,
    get_daily_register,
    list_daily_registers,
    open_daily_register,
)
from app.modules.security_tokens.dependencies import (
    require_security_token,
)
from app.modules.tenants.dependencies import (
    get_current_tenant_member,
    require_permission,
)
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

router = APIRouter(
    prefix="/daily-registers",
    tags=["Daily Registers"],
)


@router.post(
    "/open",
    response_model=DailyRegisterResponse,
    status_code=201,
)
def open_register_endpoint(
    payload: DailyRegisterOpenRequest,
    db: Session = Depends(get_db),
    current_user=Depends(require_security_token),
    membership=Depends(get_current_tenant_member),
    _permission=Depends(require_permission("registers.open")),
):
    return open_daily_register(
        db=db,
        tenant_id=membership.tenant_id,
        user_id=current_user.id,
        business_date=payload.business_date,
    )


@router.post(
    "/{register_id}/close",
    response_model=DailyRegisterResponse,
)
def close_register_endpoint(
    register_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_security_token),
    membership=Depends(get_current_tenant_member),
    _permission=Depends(require_permission("registers.close")),
):
    return close_daily_register(
        db=db,
        tenant_id=membership.tenant_id,
        user_id=current_user.id,
        register_id=register_id,
    )


@router.get(
    "",
    response_model=DailyRegisterListResponse,
)
def list_registers_endpoint(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    membership=Depends(get_current_tenant_member),
    _permission=Depends(require_permission("registers.read")),
):
    result = list_daily_registers(
        db=db,
        tenant_id=membership.tenant_id,
        page=page,
        page_size=page_size,
    )

    return {
        **result,
        "page": page,
        "page_size": page_size,
    }


@router.get(
    "/{register_id}",
    response_model=DailyRegisterDetailResponse,
)
def get_register_endpoint(
    register_id: UUID,
    db: Session = Depends(get_db),
    membership=Depends(get_current_tenant_member),
    _permission=Depends(require_permission("registers.read")),
):
    register = get_daily_register(
        db=db,
        tenant_id=membership.tenant_id,
        register_id=register_id,
    )

    balances = list(
        db.scalars(
            select(DailyRegisterBalance).where(
                DailyRegisterBalance.register_id == register.id,
                DailyRegisterBalance.tenant_id == membership.tenant_id,
            )
        ).all()
    )

    return {
        **{column.name: getattr(register, column.name) for column in register.__table__.columns},
        "balances": balances,
    }
