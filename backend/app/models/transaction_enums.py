from enum import StrEnum


class TransactionType(StrEnum):
    INCOME = "INCOME"
    EXPENSE = "EXPENSE"
    TRANSFER = "TRANSFER"


class TransactionStatus(StrEnum):
    PENDING = "PENDING"
    PAYED = "PAYED"
    DEBT = "DEBT"
    RETURNED = "RETURNED"


class TransactionNetwork(StrEnum):
    MPESA = "MPESA"
    HALOPESA = "HALOPESA"
    AIRTEL_MONEY = "AIRTEL_MONEY"
    TIGO_YAS = "TIGO_YAS"
    CASH = "CASH"


class SyncStatus(StrEnum):
    LOCAL = "LOCAL"
    SYNCED = "SYNCED"
    FAILED = "FAILED"
