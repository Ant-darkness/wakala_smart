from typing import Annotated
from uuid import UUID

from app.db.session import get_db
from app.modules.auth.dependencies import get_current_user
from app.modules.security_tokens.dependencies import require_security_token
from app.modules.tenants.dependencies import (
    get_current_tenant_member,
    require_permission,
)
from app.modules.transactions.schemas import (
    TransactionListResponse,
    TransactionQueryRequest,
    TransactionResponse,
    TransactionStatusUpdateRequest,
    TransactionSyncRequest,
    TransactionSyncResponse,
)
from app.modules.transactions.service import (
    query_transactions,
    sync_transactions,
    update_transaction_status,
)
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

router = APIRouter(
    prefix="/transactions",
    tags=["Transactions"],
)

DBSession = Annotated[Session, Depends(get_db)]


@router.post(
    "/sync",
    response_model=TransactionSyncResponse,
    status_code=status.HTTP_200_OK,
)
def sync_transaction_batch(
    payload: TransactionSyncRequest,
    db: DBSession,
    current_user=Depends(get_current_user),
    membership=Depends(get_current_tenant_member),
    _permission=Depends(require_permission("transactions.create")),
):
    return sync_transactions(
        db,
        tenant_id=membership.tenant_id,
        user_id=current_user.id,
        transactions=payload.transactions,
    )


@router.patch(
    "/{transaction_id}/status",
    response_model=TransactionResponse,
)
def change_transaction_status(
    transaction_id: UUID,
    payload: TransactionStatusUpdateRequest,
    db: DBSession,
    current_user=Depends(require_security_token),
    membership=Depends(get_current_tenant_member),
    _permission=Depends(require_permission("transactions.update")),
):
    return update_transaction_status(
        db,
        tenant_id=membership.tenant_id,
        user_id=current_user.id,
        transaction_id=transaction_id,
        new_status=payload.status,
        reason=payload.reason,
    )


@router.post(
    "/query",
    response_model=TransactionListResponse,
)
def search_transactions(
    payload: TransactionQueryRequest,
    db: DBSession,
    membership=Depends(get_current_tenant_member),
    _permission=Depends(require_permission("transactions.read")),
):
    items, total = query_transactions(
        db,
        tenant_id=membership.tenant_id,
        start_at=payload.start_at,
        end_at=payload.end_at,
        transaction_status=payload.status,
        network=payload.network,
        transaction_type=payload.transaction_type,
        page=payload.page,
        page_size=payload.page_size,
    )

    return {
        "items": items,
        "total": total,
        "page": payload.page,
        "page_size": payload.page_size,
    }
