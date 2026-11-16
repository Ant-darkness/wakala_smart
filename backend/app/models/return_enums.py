from enum import StrEnum


class ReturnDirection(StrEnum):
    SENT = "SENT"
    RECV = "RECV"


class ReturnSource(StrEnum):
    AUTO_SMS = "AUTO_SMS"
    MANUAL = "MANUAL"
