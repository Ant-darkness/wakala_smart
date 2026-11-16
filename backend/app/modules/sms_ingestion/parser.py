
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any

import regex
from app.models.transaction_enums import TransactionNetwork, TransactionType

MAX_SMS_LENGTH = 10_000
REGEX_TIMEOUT_SECONDS = 0.05

ALLOWED_GROUPS = {
    "reference",
    "amount",
    "fee",
    "commission",
    "direction",
    "transaction_type",
    "occurred_at",
}


class SmsParseError(Exception):
    """Raised when an SMS cannot be parsed safely."""


def _parse_decimal(
    value: str | None,
    field_name: str,
    required: bool = False,
) -> Decimal | None:
    if value is None or not value.strip():
        if required:
            raise SmsParseError(
                f"Required field '{field_name}' is missing."
            )
        return None

    normalized = value.strip().replace(",", "")

    try:
        result = Decimal(normalized)
    except InvalidOperation as exc:
        raise SmsParseError(
            f"Invalid decimal value for '{field_name}'."
        ) from exc

    if (
        not result.is_finite()
        or result < 0
        or result.as_tuple().exponent < -2
        or len(result.as_tuple().digits) > 18
    ):
        raise SmsParseError(
            f"Invalid numeric value for '{field_name}'."
        )

    return result


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None

    try:
        parsed = datetime.fromisoformat(
            value.strip().replace("Z", "+00:00")
        )
    except ValueError as exc:
        raise SmsParseError(
            "Invalid occurred_at. Expected ISO-8601 datetime."
        ) from exc

    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise SmsParseError(
            "SMS datetime must include a timezone offset."
        )

    return parsed


def _parse_transaction_type(
    value: str | None,
) -> TransactionType | None:
    if not value:
        return None

    try:
        return TransactionType(value.strip().upper())
    except ValueError as exc:
        raise SmsParseError(
            "Unsupported transaction_type."
        ) from exc


def _map_direction_to_type(
    value: str | None,
) -> TransactionType | None:
    if not value:
        return None

    direction = value.strip().upper()

    mapping = {
        "RECEIVED": TransactionType.INCOME,
        "SENT": TransactionType.EXPENSE,
    }

    transaction_type = mapping.get(direction)

    if transaction_type is None:
        raise SmsParseError(
            "Unsupported SMS direction. Expected RECEIVED or SENT."
        )

    return transaction_type


def parse_sms(
    network: TransactionNetwork,
    raw_body: str,
    pattern_text: str,
) -> dict[str, Any] | None:
    if not raw_body or not raw_body.strip():
        raise SmsParseError("SMS body cannot be empty.")

    if len(raw_body) > MAX_SMS_LENGTH:
        raise SmsParseError("SMS body exceeds maximum length.")

    if network == TransactionNetwork.CASH:
        raise SmsParseError(
            "Cash transactions cannot be ingested through SMS."
        )

    try:
        compiled = regex.compile(pattern_text)
    except regex.error as exc:
        raise SmsParseError(
            "Configured parser pattern is invalid."
        ) from exc

    group_names = set(compiled.groupindex.keys())

    if not group_names:
        raise SmsParseError(
            "Pattern must use named capture groups."
        )

    unknown_groups = group_names - ALLOWED_GROUPS

    if unknown_groups:
        raise SmsParseError(
            "Pattern contains unsupported capture groups."
        )

    if not {"reference", "amount"}.issubset(group_names):
        raise SmsParseError(
            "Pattern must capture reference and amount."
        )

    if not {"direction", "transaction_type"}.intersection(group_names):
        raise SmsParseError(
            "Pattern must capture direction or transaction_type."
        )

    try:
        match = compiled.search(
            raw_body,
            timeout=REGEX_TIMEOUT_SECONDS,
        )
    except TimeoutError as exc:
        raise SmsParseError(
            "Parser pattern exceeded execution time limit."
        ) from exc

    if match is None:
        return None

    groups = match.groupdict()

    reference = (groups.get("reference") or "").strip()

    if not reference:
        raise SmsParseError("Transaction reference is empty.")

    amount = _parse_decimal(
        groups.get("amount"),
        "amount",
        required=True,
    )

    if amount is None or amount <= 0:
        raise SmsParseError(
            "Transaction amount must be greater than zero."
        )

    fee = _parse_decimal(groups.get("fee"), "fee")
    commission = _parse_decimal(
        groups.get("commission"),
        "commission",
    )

    direction = groups.get("direction")
    mapped_type = _map_direction_to_type(direction)

    explicit_type = _parse_transaction_type(
        groups.get("transaction_type")
    )

    if mapped_type and explicit_type and mapped_type != explicit_type:
        raise SmsParseError(
            "SMS direction conflicts with transaction_type."
        )

    transaction_type = mapped_type or explicit_type
    occurred_at = _parse_datetime(groups.get("occurred_at"))

    return {
        "network": network.value,
        "reference": reference,
        "amount": str(amount),
        "fee": str(fee) if fee is not None else None,
        "commission": (
            str(commission) if commission is not None else None
        ),
        "direction": (
            direction.strip().upper() if direction else None
        ),
        "transaction_type": (
            transaction_type.value if transaction_type else None
        ),
        "occurred_at": (
            occurred_at.isoformat() if occurred_at is not None else None
        ),
    }
