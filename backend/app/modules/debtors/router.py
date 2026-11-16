from uuid import UUID

from app.db.session import get_db
from app.modules.debtors.schemas import (
    DebtorCreateRequest,
    DebtorListResponse,
    DebtorPaymentResponse,
    DebtorQueryRequest,
    DebtorResponse,
)
from app.modules.debtors.service import (
    create_debtor,
    list_debtors,
    pay_debtor,
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

router = APIRouter(prefix="/debtors", tags=["Debtors"])


@router.post(
    "",
    response_model=DebtorResponse,
    status_code=201,
)
def create_debtor_endpoint(
    payload: DebtorCreateRequest,
    db: Session = Depends(get_db),
    current_user=Depends(require_security_token),
    membership=Depends(get_current_tenant_member),
    _permission=Depends(require_permission("debtors.create")),
):
    return create_debtor(
        db=db,
        tenant_id=membership.tenant_id,
        user_id=current_user.id,
        transaction_id=payload.transaction_id,
        debtor_name=payload.debtor_name,
        debtor_phone=payload.debtor_phone,
        promised_at=payload.promised_at,
        reminder_enabled=payload.reminder_enabled,
    )


@router.post(
    "/query",
    response_model=DebtorListResponse,
)
def query_debtors_endpoint(
    payload: DebtorQueryRequest,
    db: Session = Depends(get_db),
    membership=Depends(get_current_tenant_member),
    _permission=Depends(require_permission("debtors.read")),
):
    return list_debtors(
        db=db,
        tenant_id=membership.tenant_id,
        query=payload,
    )


@router.post(
    "/{debtor_id}/pay",
    response_model=DebtorPaymentResponse,
)
def pay_debtor_endpoint(
    debtor_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_security_token),
    membership=Depends(get_current_tenant_member),
    _permission=Depends(require_permission("debtors.pay")),
):
    debtor = pay_debtor(
        db=db,
        tenant_id=membership.tenant_id,
        user_id=current_user.id,
        debtor_id=debtor_id,
    )

    return {
        "debtor": debtor,
        "transaction_status": "PAYED",
        "message": "Debt payment recorded successfully",
    }
