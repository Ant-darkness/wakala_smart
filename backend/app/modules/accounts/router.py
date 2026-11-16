from uuid import UUID

from app.db.session import get_db
from app.modules.accounts.schemas import (
    AccountListResponse,
    AccountResponse,
)
from app.modules.accounts.service import (
    get_account,
    list_accounts,
)
from app.modules.tenants.dependencies import (
    get_current_tenant_member,
    require_permission,
)
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

router = APIRouter(
    prefix="/accounts",
    tags=["Accounts"],
)


@router.get(
    "",
    response_model=AccountListResponse,
    dependencies=[Depends(require_permission("capital.read"))],
)
def read_accounts(
    include_inactive: bool = Query(default=False),
    db: Session = Depends(get_db),
    membership=Depends(get_current_tenant_member),
):
    accounts, total = list_accounts(
        db,
        tenant_id=membership.tenant_id,
        include_inactive=include_inactive,
    )

    return AccountListResponse(
        items=accounts,
        total=total,
    )


@router.get(
    "/{account_id}",
    response_model=AccountResponse,
    dependencies=[Depends(require_permission("capital.read"))],
)
def read_account(
    account_id: UUID,
    db: Session = Depends(get_db),
    membership=Depends(get_current_tenant_member),
):
    account = get_account(
        db,
        tenant_id=membership.tenant_id,
        account_id=account_id,
    )

    if account is None:
        raise HTTPException(
            status_code=404,
            detail="Account not found.",
        )

    return account
