from datetime import date

from app.db.session import get_db
from app.modules.analytics.schemas import (
    AgentPerformanceResponse,
    DashboardResponse,
    DebtorAnalyticsResponse,
    FinancialSummaryResponse,
    NetworkAnalyticsResponse,
)
from app.modules.analytics.service import (
    get_agent_performance,
    get_dashboard,
    get_debtor_analytics,
    get_financial_summary,
    get_network_analytics,
)
from app.modules.tenants.dependencies import (
    get_current_tenant_member,
    require_permission,
)
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

router = APIRouter(
    prefix="/analytics",
    tags=["Analytics"],
)


@router.get(
    "/financial-summary",
    response_model=FinancialSummaryResponse,
)
def financial_summary_endpoint(
    start_date: date = Query(...),
    end_date: date = Query(...),
    db: Session = Depends(get_db),
    membership=Depends(get_current_tenant_member),
    _permission=Depends(require_permission("analytics.read")),
):
    return get_financial_summary(
        db=db,
        tenant_id=membership.tenant_id,
        start_date=start_date,
        end_date=end_date,
    )


@router.get(
    "/networks",
    response_model=NetworkAnalyticsResponse,
)
def network_analytics_endpoint(
    start_date: date = Query(...),
    end_date: date = Query(...),
    db: Session = Depends(get_db),
    membership=Depends(get_current_tenant_member),
    _permission=Depends(require_permission("analytics.read")),
):
    return get_network_analytics(
        db=db,
        tenant_id=membership.tenant_id,
        start_date=start_date,
        end_date=end_date,
    )


@router.get(
    "/agents",
    response_model=AgentPerformanceResponse,
)
def agent_performance_endpoint(
    start_date: date = Query(...),
    end_date: date = Query(...),
    db: Session = Depends(get_db),
    membership=Depends(get_current_tenant_member),
    _permission=Depends(require_permission("analytics.agents.read")),
):
    return get_agent_performance(
        db=db,
        tenant_id=membership.tenant_id,
        start_date=start_date,
        end_date=end_date,
    )


@router.get(
    "/debtors",
    response_model=DebtorAnalyticsResponse,
)
def debtor_analytics_endpoint(
    db: Session = Depends(get_db),
    membership=Depends(get_current_tenant_member),
    _permission=Depends(require_permission("analytics.read")),
):
    return get_debtor_analytics(
        db=db,
        tenant_id=membership.tenant_id,
    )


@router.get(
    "/dashboard",
    response_model=DashboardResponse,
)
def dashboard_endpoint(
    business_date: date = Query(...),
    db: Session = Depends(get_db),
    membership=Depends(get_current_tenant_member),
    _permission=Depends(require_permission("analytics.read")),
):
    return get_dashboard(
        db=db,
        tenant_id=membership.tenant_id,
        business_date=business_date,
    )
