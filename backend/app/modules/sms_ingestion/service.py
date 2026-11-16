import hashlib
import re
from datetime import UTC, datetime
from uuid import UUID

from app.models.sms_enums import SmsMessageStatus
from app.models.sms_message import SmsMessage
from app.models.sms_regex_pattern import SmsRegexPattern
from app.models.transaction_enums import TransactionNetwork
from app.modules.sms_ingestion.parser import (
    SmsParseError,
    parse_sms,
)
from sqlalchemy import select
from sqlalchemy.orm import Session


def _normalize_sms(raw_body: str) -> str:
    return re.sub(r"\s+", " ", raw_body).strip()


def _fingerprint(
    network: TransactionNetwork,
    raw_body: str,
) -> str:
    normalized = _normalize_sms(raw_body)

    source = f"{network.value}|{normalized}"

    return hashlib.sha256(source.encode("utf-8")).hexdigest()


def ingest_sms(
    db: Session,
    *,
    tenant_id: UUID,
    network: TransactionNetwork,
    raw_body: str,
) -> SmsMessage:
    fingerprint = _fingerprint(network, raw_body)

    existing = db.scalar(
        select(SmsMessage).where(
            SmsMessage.tenant_id == tenant_id,
            SmsMessage.fingerprint == fingerprint,
        )
    )

    if existing:
        return existing

    patterns = db.scalars(
        select(SmsRegexPattern)
        .where(
            SmsRegexPattern.network == network,
            SmsRegexPattern.is_active.is_(True),
        )
        .order_by(
            SmsRegexPattern.priority.desc(),
            SmsRegexPattern.version.desc(),
        )
    ).all()

    parsed_payload = None
    matched_pattern_id = None
    status = SmsMessageStatus.UNMATCHED
    error_message = None

    for pattern in patterns:
        try:
            result = parse_sms(
                network=network,
                raw_body=raw_body,
                pattern_text=pattern.pattern,
            )

            if result is not None:
                parsed_payload = result
                matched_pattern_id = pattern.id
                status = SmsMessageStatus.PARSED
                break

        except SmsParseError as exc:
            # A faulty pattern must not crash the ingestion endpoint.
            error_message = str(exc)
            continue

    if status == SmsMessageStatus.UNMATCHED and error_message:
        status = SmsMessageStatus.FAILED

    message = SmsMessage(
        tenant_id=tenant_id,
        network=network,
        raw_body=raw_body,
        fingerprint=fingerprint,
        status=status,
        parsed_payload=parsed_payload,
        matched_pattern_id=matched_pattern_id,
        error_message=error_message,
        processed_at=datetime.now(UTC),
    )

    db.add(message)

    try:
        db.commit()
    except Exception:
        db.rollback()

        # A concurrent request may have inserted the same SMS.
        duplicate = db.scalar(
            select(SmsMessage).where(
                SmsMessage.tenant_id == tenant_id,
                SmsMessage.fingerprint == fingerprint,
            )
        )

        if duplicate:
            return duplicate

        raise

    db.refresh(message)
    return message


def get_sms_message(
    db: Session,
    *,
    tenant_id: UUID,
    message_id: UUID,
) -> SmsMessage | None:
    return db.scalar(
        select(SmsMessage).where(
            SmsMessage.id == message_id,
            SmsMessage.tenant_id == tenant_id,
        )
    )
