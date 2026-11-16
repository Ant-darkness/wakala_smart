from app.db.session import get_db
from app.modules.floats.schemas import (
    FloatAlertEventListResponse,
    FloatAlertSettingResponse,
    FloatAlertSettingUpsertRequest,
)
from app.modules.floats.service import (
    list_float_alert_events,
    list_float_alert_settings,
    upsert_float_alert_setting,
)
from app.modules.security_tokens.dependencies import require_security_token
from app.modules.tenants.dependencies import (
    get_current_tenant_member,
    require_permission,
)
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

router = APIRouter(
    prefix="/alerts",
    tags=["Float Alerts"],
)


@router.post(
    "/float-thresholds",
    response_model=FloatAlertSettingResponse,
    status_code=status.HTTP_200_OK,
)
def save_float_threshold(
    payload: FloatAlertSettingUpsertRequest,
    db: Session = Depends(get_db),
    membership=Depends(get_current_tenant_member),
    current_user=Depends(require_security_token),
    _permission=Depends(require_permission("floats.thresholds.manage")),
):
    try:
        return upsert_float_alert_setting(
            db,
            tenant_id=membership.tenant_id,
            user_id=current_user.id,
            account_id=payload.account_id,
            minimum_balance=payload.minimum_balance,
            is_enabled=payload.is_enabled,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get(
    "/float-thresholds",
    response_model=list[FloatAlertSettingResponse],
)
def get_float_thresholds(
    db: Session = Depends(get_db),
    membership=Depends(get_current_tenant_member),
    _permission=Depends(require_permission("floats.thresholds.read")),
):
    return list_float_alert_settings(
        db,
        tenant_id=membership.tenant_id,
    )


@router.get(
    "/float-events",
    response_model=FloatAlertEventListResponse,
)
def get_float_events(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    membership=Depends(get_current_tenant_member),
    _permission=Depends(require_permission("floats.alerts.read")),
):
    return list_float_alert_events(
        db,
        tenant_id=membership.tenant_id,
        page=page,
        page_size=page_size,
    )
