from decimal import Decimal
from uuid import UUID

from app.models.account import Account
from app.models.float_alert_event import FloatAlertEvent
from app.models.float_alert_setting import FloatAlertSetting
from app.modules.audit.service import record_user_action
from app.modules.floats.alert_engine import evaluate_float_alert_for_account
from sqlalchemy import func, select
from sqlalchemy.orm import Session


def upsert_float_alert_setting(
    db: Session,
    *,
    tenant_id: UUID,
    user_id: UUID,
    account_id: UUID,
    minimum_balance: Decimal,
    is_enabled: bool,
) -> FloatAlertSetting:
    minimum_balance = Decimal(str(minimum_balance))

    if not minimum_balance.is_finite() or minimum_balance < Decimal("0.00"):
        raise ValueError("Minimum balance must be a valid non-negative amount.")

    try:
        account = db.scalar(
            select(Account)
            .where(
                Account.id == account_id,
                Account.tenant_id == tenant_id,
            )
            .with_for_update()
        )

        if account is None:
            raise ValueError("Account not found in this business.")

        account_type = getattr(account.account_type, "value", account.account_type)

        if account_type == "CASH":
            raise ValueError("Float thresholds can only be configured for cashless accounts.")

        setting = db.scalar(
            select(FloatAlertSetting)
            .where(
                FloatAlertSetting.tenant_id == tenant_id,
                FloatAlertSetting.account_id == account_id,
            )
            .with_for_update()
        )

        before_data = None

        if setting is None:
            setting = FloatAlertSetting(
                tenant_id=tenant_id,
                account_id=account_id,
                minimum_balance=minimum_balance,
                is_enabled=is_enabled,
            )
            db.add(setting)
            action = "FLOAT_ALERT_SETTING_CREATED"
        else:
            before_data = {
                "minimum_balance": str(setting.minimum_balance),
                "is_enabled": setting.is_enabled,
            }
            setting.minimum_balance = minimum_balance
            setting.is_enabled = is_enabled
            action = "FLOAT_ALERT_SETTING_UPDATED"

        db.flush()

        record_user_action(
            db,
            user_id=user_id,
            tenant_id=tenant_id,
            action=action,
            resource_type="FLOAT_ALERT_SETTING",
            resource_id=str(setting.id),
            before_data=before_data,
            after_data={
                "account_id": str(account_id),
                "minimum_balance": str(minimum_balance),
                "is_enabled": is_enabled,
            },
        )

        evaluate_float_alert_for_account(
            db,
            tenant_id=tenant_id,
            account_id=account_id,
            account=account,
        )

        db.commit()
        db.refresh(setting)

        return setting

    except Exception:
        db.rollback()
        raise


def list_float_alert_settings(
    db: Session,
    *,
    tenant_id: UUID,
) -> list[FloatAlertSetting]:
    return list(
        db.scalars(
            select(FloatAlertSetting)
            .where(FloatAlertSetting.tenant_id == tenant_id)
            .order_by(FloatAlertSetting.created_at.desc())
        ).all()
    )


def list_float_alert_events(
    db: Session,
    *,
    tenant_id: UUID,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    query = select(FloatAlertEvent).where(FloatAlertEvent.tenant_id == tenant_id)

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0

    items = db.scalars(
        query.order_by(FloatAlertEvent.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()

    return {
        "items": list(items),
        "total": total,
        "page": page,
        "page_size": page_size,
    }
