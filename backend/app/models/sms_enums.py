from enum import StrEnum


class SmsMessageStatus(StrEnum):
    RECEIVED = "RECEIVED"
    PARSED = "PARSED"
    UNMATCHED = "UNMATCHED"
    FAILED = "FAILED"
    DUPLICATE = "DUPLICATE"
