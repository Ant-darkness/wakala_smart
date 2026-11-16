from app.db.session import get_db
from app.modules.auth.dependencies import (
    get_current_platform_user,
    get_current_user,
)
from app.modules.notifications.notice_schemas import (
    NoticeCreateRequest,
    NoticeResponse,
)
from app.modules.notifications.notice_service import (
    create_platform_notice,
    create_tenant_notice,
    list_visible_notices,
)
from app.modules.tenants.dependencies import (
    get_current_tenant_member,
    require_permission,
)
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

router = APIRouter(
    prefix="/notices",
    tags=["Notices"],
)


@router.get(
    "",
    response_model=list[NoticeResponse],
)
def get_notices(
    db: Session = Depends(get_db),
    membership=Depends(get_current_tenant_member),
    _permission=Depends(require_permission("notices.read")),
):
    return list_visible_notices(
        db,
        tenant_id=membership.tenant_id,
    )


@router.post(
    "",
    response_model=NoticeResponse,
    status_code=status.HTTP_201_CREATED,
)
def post_tenant_notice(
    payload: NoticeCreateRequest,
    db: Session = Depends(get_db),
    membership=Depends(get_current_tenant_member),
    current_user=Depends(get_current_user),
    _permission=Depends(require_permission("notices.create")),
):
    return create_tenant_notice(
        db,
        tenant_id=membership.tenant_id,
        user_id=current_user.id,
        title=payload.title,
        body=payload.body,
        starts_at=payload.starts_at,
        ends_at=payload.ends_at,
        is_published=payload.is_published,
    )


platform_router = APIRouter(
    prefix="/platform/admin/notices",
    tags=["Platform Notice Management"],
)


@platform_router.post(
    "",
    response_model=NoticeResponse,
    status_code=status.HTTP_201_CREATED,
)
def post_platform_notice(
    payload: NoticeCreateRequest,
    db: Session = Depends(get_db),
    admin=Depends(get_current_platform_user),
):
    return create_platform_notice(
        db,
        admin_id=admin.id,
        title=payload.title,
        body=payload.body,
        starts_at=payload.starts_at,
        ends_at=payload.ends_at,
        is_published=payload.is_published,
    )
