from fastapi import APIRouter

from app.modules.accounts.router import router as accounts_router
from app.modules.analytics.router import router as analytics_router
from app.modules.archives.router import router as archives_router
from app.modules.auth.router import router as auth_router
from app.modules.capital.router import router as capital_router
from app.modules.daily_registers.router import router as daily_registers_router
from app.modules.debtors.router import router as debtors_router
from app.modules.expenses.router import router as expenses_router
from app.modules.exports.router import router as exports_router
from app.modules.floats.alerts_router import router as float_alerts_router
from app.modules.members.invitation_router import router as invitations_router
from app.modules.members.router import router as members_router
from app.modules.notifications.notice_router import (
    platform_router as platform_notices_router,
)
from app.modules.notifications.notice_router import (
    router as notices_router,
)
from app.modules.notifications.router import router as notifications_router
from app.modules.platform_admin.auth_router import router as platform_auth_router
from app.modules.platform_admin.router import router as platform_admin_router
from app.modules.profiles.router import router as profiles_router
from app.modules.returns.router import router as returns_router
from app.modules.security_tokens.router import router as security_tokens_router
from app.modules.sms_ingestion.admin_router import router as sms_admin_router
from app.modules.sms_ingestion.router import router as sms_ingestion_router
from app.modules.subscriptions.router import router as subscriptions_router
from app.modules.tenants.router import router as tenants_router
from app.modules.transactions.router import router as transactions_router

api_router = APIRouter()

# Authentication and identity
api_router.include_router(auth_router)
api_router.include_router(platform_auth_router)

# Tenant and membership management
api_router.include_router(tenants_router)
api_router.include_router(members_router)
api_router.include_router(invitations_router)

# Platform administration
api_router.include_router(platform_admin_router)
api_router.include_router(platform_notices_router)

# User profiles, subscriptions and security
api_router.include_router(subscriptions_router)
api_router.include_router(profiles_router)
api_router.include_router(security_tokens_router)

# Financial operations
api_router.include_router(accounts_router)
api_router.include_router(capital_router)
api_router.include_router(transactions_router)
api_router.include_router(debtors_router)
api_router.include_router(returns_router)
api_router.include_router(expenses_router)
api_router.include_router(daily_registers_router)

# Analytics and data processing
api_router.include_router(analytics_router)
api_router.include_router(sms_ingestion_router)
api_router.include_router(sms_admin_router)
api_router.include_router(float_alerts_router)

# Notifications and records
api_router.include_router(notifications_router)
api_router.include_router(notices_router)
api_router.include_router(archives_router)
api_router.include_router(exports_router)
