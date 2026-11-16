from typing import Annotated

from app.db.session import get_db
from app.modules.auth.dependencies import get_current_platform_user
from app.modules.subscriptions.schemas import (
    AssignSubscriptionRequest,
    PlanCreateRequest,
    PlanResponse,
    PlanUpdateRequest,
    SubscriptionResponse,
)
from app.modules.subscriptions.service import (
    assign_subscription,
    create_plan,
    get_current_subscription,
    list_active_plans,
    update_plan,
)
from app.modules.tenants.dependencies import get_current_tenant_member
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

router = APIRouter(tags=["Subscriptions"])

DBSession = Annotated[Session, Depends(get_db)]


@router.get("/plans", response_model=list[PlanResponse])
def get_plans(db: DBSession):
    return list_active_plans(db)


@router.post(
    "/platform/admin/plans",
    response_model=PlanResponse,
    status_code=201,
)
def platform_create_plan(
    payload: PlanCreateRequest,
    db: DBSession,
    admin=Depends(get_current_platform_user),
):
    return create_plan(db, **payload.model_dump())


@router.patch(
    "/platform/admin/plans/{plan_id}",
    response_model=PlanResponse,
)
def platform_update_plan(
    plan_id: str,
    payload: PlanUpdateRequest,
    db: DBSession,
    admin=Depends(get_current_platform_user),
):
    from uuid import UUID

    return update_plan(
        db,
        plan_id=UUID(plan_id),
        updates=payload.model_dump(exclude_unset=True),
    )


@router.post(
    "/platform/admin/tenants/{tenant_id}/subscription",
    response_model=SubscriptionResponse,
    status_code=201,
)
def platform_assign_subscription(
    tenant_id: str,
    payload: AssignSubscriptionRequest,
    db: DBSession,
    admin=Depends(get_current_platform_user),
):
    from uuid import UUID

    return assign_subscription(
        db,
        tenant_id=UUID(tenant_id),
        plan_id=payload.plan_id,
        subscription_status=payload.status,
        starts_at=payload.starts_at,
        ends_at=payload.ends_at,
        trial_ends_at=payload.trial_ends_at,
    )


@router.get(
    "/subscription/current",
    response_model=SubscriptionResponse | None,
)
def get_tenant_subscription(
    db: DBSession,
    membership=Depends(get_current_tenant_member),
):
    return get_current_subscription(db, membership.tenant_id)
