from app.db.session import get_db
from app.modules.returns.schemas import (
    ReturnCreateRequest,
    ReturnListResponse,
    ReturnQueryRequest,
    ReturnResponse,
)
from app.modules.returns.service import (
    create_manual_return,
    query_returns,
)
from app.modules.security_tokens.dependencies import (
    require_security_token,
)
from app.modules.tenants.dependencies import (
    get_current_tenant_member,
    require_permission,
)
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

router = APIRouter(
    prefix="/returns",
    tags=["Returned Transactions"],
)


@router.post(
    "",
    response_model=ReturnResponse,
    status_code=201,
)
def create_return_endpoint(
    payload: ReturnCreateRequest,
    db: Session = Depends(get_db),
    current_user=Depends(require_security_token),
    membership=Depends(get_current_tenant_member),
    _permission=Depends(require_permission("returns.create")),
):
    return create_manual_return(
        db=db,
        tenant_id=membership.tenant_id,
        user_id=current_user.id,
        transaction_id=payload.transaction_id,
        reference=payload.reference,
        direction=payload.direction,
        amount=payload.amount,
        reason=payload.reason,
    )


@router.post(
    "/query",
    response_model=ReturnListResponse,
)
def query_returns_endpoint(
    payload: ReturnQueryRequest,
    db: Session = Depends(get_db),
    membership=Depends(get_current_tenant_member),
    _permission=Depends(require_permission("returns.read")),
):
    return query_returns(
        db=db,
        tenant_id=membership.tenant_id,
        query=payload,
    )
