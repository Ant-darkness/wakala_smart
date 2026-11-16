from enum import StrEnum


class TenantStatus(StrEnum):
    ACTIVE = "ACTIVE"
    RESTRICTED = "RESTRICTED"
    LOCKED = "LOCKED"
    SOFT_DELETED = "SOFT_DELETED"


class UserStatus(StrEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    SUSPENDED = "SUSPENDED"


class AuthProvider(StrEnum):
    LOCAL = "LOCAL"
    GOOGLE = "GOOGLE"


class MembershipStatus(StrEnum):
    ACTIVE = "ACTIVE"
    INVITED = "INVITED"
    SUSPENDED = "SUSPENDED"


class RoleCode(StrEnum):
    BUSINESS_OWNER = "BUSINESS_OWNER"
    AGENT_OPERATOR = "AGENT_OPERATOR"


class PlatformRoleCode(StrEnum):
    SUPER_ADMIN = "SUPER_ADMIN"
