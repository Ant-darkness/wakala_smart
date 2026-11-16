
import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Plan(Base):
    __tablename__ = "plans"

    __table_args__ = (
        UniqueConstraint(
            "code",
            name="uq_plans_code",
        ),
        CheckConstraint(
            "price >= 0",
            name="ck_plans_price_nonnegative",
        ),
        CheckConstraint(
            "length(trim(code)) > 0",
            name="ck_plans_code_nonempty",
        ),
        CheckConstraint(
            "length(trim(name)) > 0",
            name="ck_plans_name_nonempty",
        ),
        CheckConstraint(
            "length(currency) = 3",
            name="ck_plans_currency_length",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    code: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=Decimal("0.00"),
        server_default=text("0.00"),
    )

    currency: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
        default="TZS",
        server_default="TZS",
    )

    billing_interval: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="MONTHLY",
        server_default="MONTHLY",
    )

    limits: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
        server_default=text("'{}'"),
    )

    features: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
        server_default=text("'{}'"),
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )
