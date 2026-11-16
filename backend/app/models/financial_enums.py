from enum import StrEnum


class AccountType(StrEnum):
    CASH = "CASH"
    MPESA = "MPESA"
    HALOPESA = "HALOPESA"
    AIRTEL_MONEY = "AIRTEL_MONEY"
    TIGO_YAS = "TIGO_YAS"


class CapitalAdjustmentType(StrEnum):
    FROM_CASH = "FROM_CASH"
    OUTSIDE_CAPITAL = "OUTSIDE_CAPITAL"
    FLOAT_SHIFT = "FLOAT_SHIFT"


class FinancialEntryType(StrEnum):
    DEBIT = "DEBIT"
    CREDIT = "CREDIT"


class ExpenseStatus(StrEnum):
    FROM_CAPITAL = "FROM_CAPITAL"
    EXTRA = "EXTRA"
