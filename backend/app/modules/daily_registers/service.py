from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from app.models.account import Account
from app.models.daily_register import DailyRegister
from app.models.daily_register_balance import DailyRegisterBalance
from app.models.register_enums import DailyRegisterStatus
from app.modules.audit.service import record_user_action
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session


def open_daily_register(
    db: Session,
    tenant_id: UUID,
    user_id: UUID,
    business_date,
) -> DailyRegister:
    try:
        open_register = db.scalar(
            select(DailyRegister.id)
            .where(
                DailyRegister.tenant_id == tenant_id,
                DailyRegister.status == DailyRegisterStatus.OPEN,
            )
            .with_for_update()
        )

        if open_register:
            raise HTTPException(
                status_code=409,
                detail="Close the existing open register before opening another",
            )

        existing = db.scalar(
            select(DailyRegister.id).where(
                DailyRegister.tenant_id == tenant_id,
                DailyRegister.business_date == business_date,
            )
        )

        if existing:
            raise HTTPException(
                status_code=409,
                detail="A register already exists for this business date",
            )

        accounts = list(
            db.scalars(
                select(Account)
                .where(
                    Account.tenant_id == tenant_id,
                    Account.is_active.is_(True),
                )
                .order_by(Account.id)
                .with_for_update()
            ).all()
        )

        if not accounts:
            raise HTTPException(
                status_code=409,
                detail="Create at least one account before opening a register",
            )

        opening_capital = sum(
            (account.balance for account in accounts),
            Decimal("0.00"),
        )

        register = DailyRegister(
            tenant_id=tenant_id,
            business_date=business_date,
            status=DailyRegisterStatus.OPEN,
            opening_master_capital=opening_capital,
            opened_by_user_id=user_id,
        )

        db.add(register)
        db.flush()

        for account in accounts:
            db.add(
                DailyRegisterBalance(
                    tenant_id=tenant_id,
                    register_id=register.id,
                    account_id=account.id,
                    opening_balance=account.balance,
                )
            )

        record_user_action(
            db=db,
            user_id=user_id,
            tenant_id=tenant_id,
            action="DAILY_REGISTER_OPENED",
            resource_type="DAILY_REGISTER",
            resource_id=str(register.id),
            after_data={
                "business_date": business_date.isoformat(),
                "opening_master_capital": str(opening_capital),
                "account_count": len(accounts),
            },
        )

        db.commit()
        db.refresh(register)

        return register

    except HTTPException:
        db.rollback()
        raise

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="A register already exists for this business date",
        )

    except Exception:
        db.rollback()
        raise


def close_daily_register(
    db: Session,
    tenant_id: UUID,
    user_id: UUID,
    register_id: UUID,
) -> DailyRegister:
    try:
        register = db.scalar(
            select(DailyRegister)
            .where(
                DailyRegister.id == register_id,
                DailyRegister.tenant_id == tenant_id,
            )
            .with_for_update()
        )

        if register is None:
            raise HTTPException(
                status_code=404,
                detail="Daily register not found",
            )

        if register.status == DailyRegisterStatus.CLOSED:
            raise HTTPException(
                status_code=409,
                detail="This daily register is already closed",
            )

        accounts = list(
            db.scalars(
                select(Account)
                .where(
                    Account.tenant_id == tenant_id,
                    Account.is_active.is_(True),
                )
                .order_by(Account.id)
                .with_for_update()
            ).all()
        )

        now = datetime.now(UTC)

        closing_capital = sum(
            (account.balance for account in accounts),
            Decimal("0.00"),
        )

        account_map = {account.id: account for account in accounts}

        snapshots = list(
            db.scalars(
                select(DailyRegisterBalance)
                .where(
                    DailyRegisterBalance.register_id == register.id,
                    DailyRegisterBalance.tenant_id == tenant_id,
                )
                .with_for_update()
            ).all()
        )

        for snapshot in snapshots:
            account = account_map.get(snapshot.account_id)

            if account is None:
                continue

            snapshot.closing_balance = account.balance
            snapshot.closed_at = now

        register.closing_master_capital = closing_capital
        register.status = DailyRegisterStatus.CLOSED
        register.closed_by_user_id = user_id
        register.closed_at = now

        record_user_action(
            db=db,
            user_id=user_id,
            tenant_id=tenant_id,
            action="DAILY_REGISTER_CLOSED",
            resource_type="DAILY_REGISTER",
            resource_id=str(register.id),
            before_data={
                "status": DailyRegisterStatus.OPEN.value,
            },
            after_data={
                "status": DailyRegisterStatus.CLOSED.value,
                "closing_master_capital": str(closing_capital),
                "closed_at": now.isoformat(),
            },
        )

        db.commit()
        db.refresh(register)

        return register

    except HTTPException:
        db.rollback()
        raise

    except Exception:
        db.rollback()
        raise


def get_daily_register(
    db: Session,
    tenant_id: UUID,
    register_id: UUID,
) -> DailyRegister:
    register = db.scalar(
        select(DailyRegister).where(
            DailyRegister.id == register_id,
            DailyRegister.tenant_id == tenant_id,
        )
    )

    if register is None:
        raise HTTPException(
            status_code=404,
            detail="Daily register not found",
        )

    return register


def list_daily_registers(
    db: Session,
    tenant_id: UUID,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    statement = select(DailyRegister).where(DailyRegister.tenant_id == tenant_id)

    total = db.scalar(select(func.count()).select_from(statement.subquery())) or 0

    items = list(
        db.scalars(
            statement.order_by(DailyRegister.business_date.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
    )

    return {
        "items": items,
        "total": total,
    }
