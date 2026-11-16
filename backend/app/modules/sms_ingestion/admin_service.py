from uuid import UUID

from app.models.sms_regex_pattern import SmsRegexPattern
from app.models.transaction_enums import TransactionNetwork
from app.modules.audit.service import record_platform_action
from sqlalchemy import select
from sqlalchemy.orm import Session


def create_sms_pattern(
    db: Session,
    *,
    admin_id: UUID,
    network: TransactionNetwork,
    name: str,
    description: str | None,
    pattern: str,
    version: int,
    priority: int,
) -> SmsRegexPattern:
    existing = db.scalar(
        select(SmsRegexPattern).where(
            SmsRegexPattern.network == network,
            SmsRegexPattern.name == name,
            SmsRegexPattern.version == version,
        )
    )

    if existing:
        raise ValueError("A parser with this network, name and version already exists.")

    item = SmsRegexPattern(
        network=network,
        name=name,
        description=description,
        pattern=pattern,
        version=version,
        priority=priority,
        is_active=False,
        created_by_platform_user_id=admin_id,
    )

    db.add(item)
    db.flush()

    record_platform_action(
        db,
        admin_id=admin_id,
        action="SMS_PARSER_PATTERN_CREATED",
        resource_type="SMS_REGEX_PATTERN",
        resource_id=str(item.id),
        after_data={
            "network": network.value,
            "name": name,
            "version": version,
            "priority": priority,
        },
    )

    db.commit()
    db.refresh(item)

    return item


def list_sms_patterns(
    db: Session,
    *,
    network: TransactionNetwork | None = None,
) -> list[SmsRegexPattern]:
    query = select(SmsRegexPattern).order_by(
        SmsRegexPattern.network,
        SmsRegexPattern.name,
        SmsRegexPattern.version.desc(),
    )

    if network is not None:
        query = query.where(SmsRegexPattern.network == network)

    return list(db.scalars(query).all())


def set_sms_pattern_active(
    db: Session,
    *,
    admin_id: UUID,
    pattern_id: UUID,
    is_active: bool,
) -> SmsRegexPattern:
    item = db.scalar(
        select(SmsRegexPattern).where(SmsRegexPattern.id == pattern_id).with_for_update()
    )

    if item is None:
        raise ValueError("SMS parser pattern not found.")

    previous = item.is_active
    item.is_active = is_active

    record_platform_action(
        db,
        admin_id=admin_id,
        action=("SMS_PARSER_PATTERN_ACTIVATED" if is_active else "SMS_PARSER_PATTERN_DEACTIVATED"),
        resource_type="SMS_REGEX_PATTERN",
        resource_id=str(item.id),
        before_data={"is_active": previous},
        after_data={"is_active": is_active},
    )

    db.commit()
    db.refresh(item)

    return item
