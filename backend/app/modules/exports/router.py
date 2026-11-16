from datetime import datetime
from typing import Annotated

from app.db.session import get_db
from app.modules.exports.service import (
    export_expenses_csv,
    export_transactions_csv,
)
from app.modules.tenants.dependencies import require_permission
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

router = APIRouter(prefix="/exports", tags=["Exports"])


@router.get("/transactions.csv")
def download_transactions(
    date_from: Annotated[datetime | None, Query()] = None,
    date_to: Annotated[datetime | None, Query()] = None,
    db: Session = Depends(get_db),
    membership=Depends(require_permission("transactions.export")),
):
    rows = export_transactions_csv(
        db,
        tenant_id=membership.tenant_id,
        date_from=date_from,
        date_to=date_to,
    )

    return StreamingResponse(
        rows,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="wakala_transactions.csv"'},
    )


@router.get("/expenses.csv")
def download_expenses(
    date_from: Annotated[datetime | None, Query()] = None,
    date_to: Annotated[datetime | None, Query()] = None,
    db: Session = Depends(get_db),
    membership=Depends(require_permission("expenses.export")),
):
    rows = export_expenses_csv(
        db,
        tenant_id=membership.tenant_id,
        date_from=date_from,
        date_to=date_to,
    )

    return StreamingResponse(
        rows,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="wakala_expenses.csv"'},
    )
