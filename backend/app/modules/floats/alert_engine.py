from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from app.models.account import Account
from app.models.float_alert_enums import FloatAlertStatus
from app.models.float_alert_event import FloatAlertEvent
from app.models.float_alert_setting import FloatAlertSetting
from sqlalchemy import select
from sqlalchemy.orm import Session


def evaluate_float_alert_for_account(
    db: Session,
    *,
    tenant_id: UUID,
    account_id: UUID,
    account: Account | None = None,
) -> FloatAlertEvent | None:
    """
    Evaluate one account's float alert.

    The caller owns the transaction and must commit or roll back.
    The account row is locked here unless the caller supplies an
    account that it has already locked in the current transaction.
    """

    if account is None:
        account = db.scalar(
            select(Account)
            .where(
                Account.id == account_id,
                Account.tenant_id == tenant_id,
            )
            .with_for_update()
        )
    elif account.id != account_id or account.tenant_id != tenant_id:
        raise ValueError("Account does not belong to the specified tenant.")

    if account is None:
        return None

    setting = db.scalar(
        select(FloatAlertSetting)
        .where(
            FloatAlertSetting.tenant_id == tenant_id,
            FloatAlertSetting.account_id == account_id,
        )
        .with_for_update()
    )

    active_event = db.scalar(
        select(FloatAlertEvent)
        .where(
            FloatAlertEvent.tenant_id == tenant_id,
            FloatAlertEvent.account_id == account_id,
            FloatAlertEvent.status == FloatAlertStatus.ACTIVE,
        )
        .with_for_update()
    )

    if setting is None or not setting.is_enabled:
        if active_event is not None:
            active_event.status = FloatAlertStatus.RESOLVED
            active_event.resolved_at = datetime.now(UTC)

        db.flush()
        return None

    current_balance = Decimal(str(account.balance))
    minimum_balance = Decimal(str(setting.minimum_balance))

    if current_balance <= minimum_balance:
        if active_event is not None:
            active_event.observed_balance = current_balance
            active_event.minimum_balance = minimum_balance
            db.flush()
            return active_event

        event = FloatAlertEvent(
            tenant_id=tenant_id,
            account_id=account_id,
            minimum_balance=minimum_balance,
            observed_balance=current_balance,
            status=FloatAlertStatus.ACTIVE,
            message=(
                f"Float is at or below the configured minimum. Current balance: {current_balance}."
            ),
        )

        db.add(event)
        db.flush()
        return event

    if active_event is not None:
        active_event.status = FloatAlertStatus.RESOLVED
        active_event.resolved_at = datetime.now(UTC)
        active_event.observed_balance = current_balance
        db.flush()

    return None


def evaluate_all_float_alerts(
    db: Session,
    *,
    tenant_id: UUID,
) -> int:
    """
    Evaluate every enabled float alert for a tenant.

    One transaction is used for the whole evaluation batch.
    """

    account_ids = db.scalars(
        select(FloatAlertSetting.account_id)
        .where(
            FloatAlertSetting.tenant_id == tenant_id,
            FloatAlertSetting.is_enabled.is_(True),
        )
        .order_by(FloatAlertSetting.account_id)
    ).all()

    evaluated = 0

    try:
        for account_id in account_ids:
            evaluate_float_alert_for_account(
                db,
                tenant_id=tenant_id,
                account_id=account_id,
            )
            evaluated += 1

        db.commit()
        return evaluated

    except Exception:
        db.rollback()
        raise
