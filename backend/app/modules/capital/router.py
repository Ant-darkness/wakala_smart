from typing import Annotated

from app.db.session import get_db
from app.modules.capital.schemas import (
    AccountCreateRequest,
    AccountResponse,
    CapitalAdjustmentResponse,
    CapitalConversionRequest,
    CapitalInjectionRequest,
    CapitalMasterResponse,
    FinancialHistoryResponse,
    FloatShiftRequest,
)
from app.modules.capital.service import (
    convert_capital,
    create_account,
    get_capital_history,
    get_capital_master,
    inject_capital,
    shift_float,
)
from app.modules.security_tokens.dependencies import require_security_token
from app.modules.tenants.dependencies import (
    get_current_tenant_member,
    require_permission,
)
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

router = APIRouter(
    prefix="/capital",
    tags=["Capital"],
)

DBSession = Annotated[Session, Depends(get_db)]


@router.get(
    "/master",
    response_model=CapitalMasterResponse,
)
def capital_master(
    db: DBSession,
    membership=Depends(get_current_tenant_member),
    _permission=Depends(require_permission("capital.read")),
):
    return get_capital_master(
        db,
        tenant_id=membership.tenant_id,
    )


@router.post(
    "/accounts",
    response_model=AccountResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_account(
    payload: AccountCreateRequest,
    db: DBSession,
    current_user=Depends(require_security_token),
    membership=Depends(get_current_tenant_member),
    _permission=Depends(require_permission("capital.manage")),
):
    return create_account(
        db,
        tenant_id=membership.tenant_id,
        actor_user_id=current_user.id,
        name=payload.name,
        account_type=payload.account_type,
    )


@router.post(
    "/convert",
    response_model=CapitalAdjustmentResponse,
)
def capital_conversion(
    payload: CapitalConversionRequest,
    db: DBSession,
    current_user=Depends(require_security_token),
    membership=Depends(get_current_tenant_member),
    _permission=Depends(require_permission("capital.manage")),
):
    return convert_capital(
        db,
        tenant_id=membership.tenant_id,
        actor_user_id=current_user.id,
        source_account_id=payload.source_account_id,
        destination_account_id=payload.destination_account_id,
        amount=payload.amount,
        reason=payload.reason,
    )


@router.post(
    "/inject",
    response_model=CapitalAdjustmentResponse,
)
def capital_injection(
    payload: CapitalInjectionRequest,
    db: DBSession,
    current_user=Depends(require_security_token),
    membership=Depends(get_current_tenant_member),
    _permission=Depends(require_permission("capital.manage")),
):
    return inject_capital(
        db,
        tenant_id=membership.tenant_id,
        actor_user_id=current_user.id,
        destination_account_id=payload.destination_account_id,
        amount=payload.amount,
        reason=payload.reason,
    )


@router.post(
    "/float-shift",
    response_model=CapitalAdjustmentResponse,
)
def capital_float_shift(
    payload: FloatShiftRequest,
    db: DBSession,
    current_user=Depends(require_security_token),
    membership=Depends(get_current_tenant_member),
    _permission=Depends(require_permission("capital.manage")),
):
    return shift_float(
        db,
        tenant_id=membership.tenant_id,
        actor_user_id=current_user.id,
        source_account_id=payload.source_account_id,
        destination_account_id=payload.destination_account_id,
        amount=payload.amount,
        reason=payload.reason,
    )


@router.get(
    "/history",
    response_model=FinancialHistoryResponse,
)
def capital_history(
    db: DBSession,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    membership=Depends(get_current_tenant_member),
    _permission=Depends(require_permission("capital.read")),
):
    items, total = get_capital_history(
        db,
        tenant_id=membership.tenant_id,
        page=page,
        page_size=page_size,
    )

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }
