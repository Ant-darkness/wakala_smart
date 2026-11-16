from datetime import UTC, datetime
from uuid import UUID

from app.models.plan import Plan
from app.models.subscription import Subscription
from app.models.tenant import Tenant
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session


def list_active_plans(db: Session) -> list[Plan]:
    statement = select(Plan).where(Plan.is_active.is_(True)).order_by(Plan.price.asc())
    return list(db.scalars(statement).all())


def get_current_subscription(
    db: Session,
    tenant_id: UUID,
) -> Subscription | None:
    statement = (
        select(Subscription)
        .where(Subscription.tenant_id == tenant_id)
        .order_by(Subscription.created_at.desc())
        .limit(1)
    )
    return db.scalar(statement)


def assign_subscription(
    db: Session,
    *,
    tenant_id: UUID,
    plan_id: UUID,
    subscription_status: str,
    starts_at: datetime | None = None,
    ends_at: datetime | None = None,
    trial_ends_at: datetime | None = None,
) -> Subscription:
    tenant = db.scalar(select(Tenant).where(Tenant.id == tenant_id).with_for_update())

    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found.",
        )

    plan = db.get(Plan, plan_id)

    if plan is None or not plan.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Active plan not found.",
        )

    allowed_statuses = {"TRIAL", "ACTIVE", "PAST_DUE", "CANCELLED", "EXPIRED"}

    if subscription_status not in allowed_statuses:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid subscription status.",
        )

    if ends_at and starts_at and ends_at <= starts_at:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Subscription end date must be after start date.",
        )

    now = datetime.now(UTC)

    subscription = Subscription(
        tenant_id=tenant_id,
        plan_id=plan_id,
        status=subscription_status,
        starts_at=starts_at or now,
        ends_at=ends_at,
        trial_ends_at=trial_ends_at,
    )

    db.add(subscription)
    db.commit()
    db.refresh(subscription)

    return subscription


def create_plan(
    db: Session,
    *,
    code: str,
    name: str,
    description: str | None,
    price,
    currency: str,
    billing_interval: str,
    limits: dict,
    features: dict,
) -> Plan:
    normalized_code = code.strip().upper()

    existing = db.scalar(select(Plan).where(Plan.code == normalized_code))

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A plan with this code already exists.",
        )

    plan = Plan(
        code=normalized_code,
        name=name.strip(),
        description=description,
        price=price,
        currency=currency.upper(),
        billing_interval=billing_interval.upper(),
        limits=limits,
        features=features,
        is_active=True,
    )

    db.add(plan)
    db.commit()
    db.refresh(plan)

    return plan


def update_plan(
    db: Session,
    *,
    plan_id: UUID,
    updates: dict,
) -> Plan:
    plan = db.scalar(select(Plan).where(Plan.id == plan_id).with_for_update())

    if plan is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plan not found.",
        )

    for field, value in updates.items():
        if value is not None:
            setattr(plan, field, value)

    db.commit()
    db.refresh(plan)

    return plan


def list_platform_subscriptions(
    db: Session,
    *,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list, int]:
    from sqlalchemy import func

    statement = (
        select(
            Subscription,
            Tenant.name.label("tenant_name"),
            Plan.name.label("plan_name"),
        )
        .join(Tenant, Tenant.id == Subscription.tenant_id)
        .join(Plan, Plan.id == Subscription.plan_id)
        .order_by(Subscription.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )

    count_statement = select(func.count(Subscription.id))

    rows = db.execute(statement).all()
    total = db.scalar(count_statement) or 0

    return rows, total
