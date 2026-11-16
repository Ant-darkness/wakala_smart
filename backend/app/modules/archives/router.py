from uuid import UUID

from app.db.session import get_db
from app.modules.archives.schemas import (
    DailyArchiveListResponse,
    DailyArchiveResponse,
)
from app.modules.archives.service import (
    create_daily_archive,
    list_daily_archives,
)
from app.modules.tenants.dependencies import require_permission
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

router = APIRouter(prefix="/archives", tags=["Daily Archives"])


@router.post(
    "/{register_id}",
    response_model=DailyArchiveResponse,
)
def archive_register(
    register_id: UUID,
    db: Session = Depends(get_db),
    membership=Depends(require_permission("archives.create")),
):
    return create_daily_archive(
        db,
        tenant_id=membership.tenant_id,
        register_id=register_id,
    )


@router.get(
    "",
    response_model=DailyArchiveListResponse,
)
def get_archives(
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
    membership=Depends(require_permission("archives.read")),
):
    return list_daily_archives(
        db,
        tenant_id=membership.tenant_id,
        page=page,
        page_size=page_size,
    )
