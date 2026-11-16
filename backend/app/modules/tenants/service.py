import re
import uuid

from app.models.enums import MembershipStatus, RoleCode, TenantStatus
from app.models.permission import Permission
from app.models.role import Role
from app.models.role_permission import RolePermission
from app.models.tenant import Tenant
from app.models.tenant_member import TenantMember
from app.models.user import User
from app.modules.ledger.chart import seed_ledger_accounts
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

OWNER_PERMISSIONS = {
    "tenant.read",
    "tenant.update",
    "members.read",
    "members.create",
    "members.update",
    "members.suspend",
    "accounts.read",
    "accounts.manage",
    "transactions.read",
    "transactions.create",
    "transactions.update",
    "transactions.export",
    "expenses.read",
    "expenses.create",
    "expenses.update",
    "capital.read",
    "capital.manage",
    "registers.read",
    "registers.manage",
    "debtors.read",
    "debtors.manage",
    "returns.read",
    "returns.manage",
    "analytics.read",
    "alerts.manage",
    "archives.read",
    "expenses.categories.create",
    "registers.open",
    "registers.close",
    "returns.create",
    "analytics.agents.read",
    "sms.ingest",
    "sms.read",
    "floats.thresholds.manage",
    "floats.thresholds.read",
    "floats.alerts.read",
    "notices.create",
    "notices.read",
    "archives.create",
    "expenses.export",
}

AGENT_PERMISSIONS = {
    "tenant.read",
    "accounts.read",
    "transactions.read",
    "transactions.create",
    "transactions.update",
    "expenses.read",
    "expenses.create",
    "registers.read",
    "registers.manage",
    "debtors.read",
    "debtors.manage",
    "returns.read",
    "returns.manage",
    "returns.create",
    "sms.ingest",
    "notices.read",
}


BUILT_IN_PERMISSIONS = {
    "tenant.read": "View business information",
    "tenant.update": "Update business information",
    "members.read": "View business members",
    "members.create": "Add business members",
    "members.update": "Update member roles",
    "members.suspend": "Suspend business members",
    "accounts.read": "View accounts",
    "accounts.manage": "Manage accounts",
    "transactions.read": "View transactions",
    "transactions.create": "Create transactions",
    "transactions.update": "Update transactions",
    "transactions.export": "Export transactions",
    "expenses.read": "View expenses",
    "expenses.create": "Record expenses",
    "expenses.update": "Update expenses",
    "capital.read": "View capital",
    "capital.manage": "Manage capital",
    "registers.read": "View daily registers",
    "registers.manage": "Manage daily registers",
    "debtors.read": "View debtors",
    "debtors.manage": "Manage debtors",
    "returns.read": "View returned transactions",
    "returns.manage": "Manage returned transactions",
    "analytics.read": "View business analytics",
    "alerts.manage": "Manage float alerts",
    "archives.read": "View daily archives",
    "expenses.categories.create": "Create expense categories",
    "registers.open": "Open daily registers",
    "registers.close": "Close daily registers",
    "returns.create": "Create returned transactions",
    "analytics.agents.read": "View agent performance",
    "sms.ingest": "Submit SMS messages for parsing",
    "sms.read": "View SMS ingestion records",
    "floats.thresholds.manage": "Manage float thresholds",
    "floats.thresholds.read": "View float thresholds",
    "floats.alerts.read": "View float alert events",
    "notices.create": "Create business notices",
    "notices.read": "View business notices",
    "archives.create": "Create daily archives",
    "expenses.export": "Export expense records",
}

# {
#    "code": "capital.read",
#    "name": "View business capital",
#    "description": "View account balances and capital history.",
# },
# {
#    "code": "capital.manage",
#    "name": "Manage business capital",
#    "description": "Create accounts and perform capital adjustments.",
# },

# {
#    "code": "transactions.read",
#    "name": "View transactions",
#    "description": "View and search business transactions.",
# },
# {
#    "code": "transactions.create",
#    "name": "Sync transactions",
#    "description": "Synchronize transaction records from agent devices.",
# },
# {
#    "code": "transactions.update",
#    "name": "Update transaction status",
#    "description": "Change permitted transaction statuses.",
# },
# {
#    "code": "debtors.read",
#    "name": "Read debtors",
#    "description": "View tenant debt records",
# },
# {
#    "code": "debtors.create",
#    "name": "Create debtors",
#    "description": "Mark eligible transactions as debt",
# },
# {
#    "code": "debtors.pay",
#    "name": "Pay debtors",
#    "description": "Record debt payment",
# },

# {
#    "code": "returns.read",
#    "name": "Read returned transactions",
#    "description": "View returned transaction records",
# },
# {
#    "code": "returns.create",
#    "name": "Create returned transactions",
#    "description": "Record manually returned transactions",
# },
# {
#    "code": "expenses.read",
#    "name": "Read expenses",
#    "description": "View tenant expenses and categories",
# },
# {
#    "code": "expenses.create",
#    "name": "Create expenses",
#    "description": "Record tenant expenses",
# },
# {
#    "code": "expenses.categories.create",
#    "name": "Create expense categories",
#    "description": "Create tenant expense categories",
# },
# {
#    "code": "registers.read",
#    "name": "Read daily registers",
#    "description": "View daily business registers",
# },
# {
#    "code": "registers.open",
#    "name": "Open daily register",
#    "description": "Open a daily business register",
# },
# {
#    "code": "registers.close",
#    "name": "Close daily register",
#    "description": "Close a daily business register",
# },

# {
#    "code": "analytics.read",
#    "name": "Read analytics",
#    "description": "View tenant financial and business analytics",
# },
# {
#    "code": "analytics.agents.read",
#    "name": "Read agent performance",
#    "description": "View individual agent performance",
# },

# {
#    "code": "sms.ingest",
#    "name": "Ingest SMS Messages",
#    "description": "Submit SMS messages for transaction parsing.",
# },
# {
#    "code": "sms.read",
#    "name": "Read SMS Messages",
#    "description": "View SMS ingestion and parsing results.",
# },

# {
#    "code": "floats.thresholds.manage",
#    "name": "Manage Float Thresholds",
#    "description": "Create and update float alert thresholds.",
# },
# {
#    "code": "floats.thresholds.read",
#    "name": "Read Float Thresholds",
#    "description": "View configured float thresholds.",
# },
# {
#    "code": "floats.alerts.read",
#    "name": "Read Float Alerts",
#    "description": "View float alert events.",
# },
# {
#    "code": "notices.create",
#    "name": "Create Business Notices",
#    "description": "Create notices for members of a business.",
# },
# {
#    "code": "notices.read",
#    "name": "Read Business Notices",
#    "description": "Read notices visible to the business.",
# },
# "archives.create",
# "archives.read",
# "transactions.export",
# "expenses.export",


def _slugify(value: str) -> str:
    normalized = value.strip().lower()
    normalized = re.sub(r"[^a-z0-9]+", "-", normalized)
    return normalized.strip("-")


def _get_or_create_permission(
    db: Session,
    code: str,
    description: str,
) -> Permission:
    permission = db.scalar(select(Permission).where(Permission.code == code))

    if permission is None:
        permission = Permission(
            code=code,
            name=code.replace(".", " ").title(),
            description=description,
        )
        db.add(permission)
        db.flush()

    return permission


def _create_role(
    db: Session,
    tenant_id: uuid.UUID,
    code: str,
    name: str,
    description: str,
    permission_codes: set[str],
) -> Role:
    role = Role(
        tenant_id=tenant_id,
        code=code,
        name=name,
        description=description,
        is_system=True,
    )

    db.add(role)
    db.flush()

    for permission_code in sorted(permission_codes):
        permission = _get_or_create_permission(
            db,
            permission_code,
            BUILT_IN_PERMISSIONS[permission_code],
        )

        db.add(
            RolePermission(
                role_id=role.id,
                permission_id=permission.id,
            )
        )

    return role


def create_tenant(
    db: Session,
    owner: User,
    name: str,
) -> Tenant:
    clean_name = name.strip()

    if not owner.is_email_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Verify your email before creating a business.",
        )

    if not clean_name:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Business name is required.",
        )

    slug = f"{_slugify(clean_name) or 'business'}-{uuid.uuid4().hex[:8]}"

    try:
        tenant = Tenant(
            name=clean_name,
            slug=slug,
            status=TenantStatus.ACTIVE,
        )

        db.add(tenant)
        db.flush()

        seed_ledger_accounts(
            db,
            tenant_id=tenant.id,
        )

        owner_role = _create_role(
            db=db,
            tenant_id=tenant.id,
            code=RoleCode.BUSINESS_OWNER.value,
            name="Business Owner",
            description="Full management access within this business.",
            permission_codes=OWNER_PERMISSIONS,
        )

        _create_role(
            db=db,
            tenant_id=tenant.id,
            code=RoleCode.AGENT_OPERATOR.value,
            name="Agent Operator",
            description="Operational access within assigned business.",
            permission_codes=AGENT_PERMISSIONS,
        )

        membership = TenantMember(
            tenant_id=tenant.id,
            user_id=owner.id,
            role_id=owner_role.id,
            status=MembershipStatus.ACTIVE,
        )

        db.add(membership)
        db.commit()
        db.refresh(tenant)

        return tenant

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Unable to create business due to a data conflict.",
        ) from None

    except Exception:
        db.rollback()
        raise


def get_user_tenants(
    db: Session,
    user: User,
) -> list[Tenant]:
    statement = (
        select(Tenant)
        .join(TenantMember, TenantMember.tenant_id == Tenant.id)
        .where(
            TenantMember.user_id == user.id,
            TenantMember.status == MembershipStatus.ACTIVE,
            Tenant.status == TenantStatus.ACTIVE,
            Tenant.deleted_at.is_(None),
        )
        .order_by(Tenant.created_at.desc())
    )

    return list(db.scalars(statement).all())
