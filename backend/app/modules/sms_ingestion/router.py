
from uuid import UUID

from app.db.session import get_db
from app.modules.sms_ingestion.schemas import (
    SmsIngestRequest,
    SmsIngestResponse,
)
from app.modules.sms_ingestion.service import (
    get_sms_message,
    ingest_sms,
)
from app.modules.tenants.dependencies import (
    get_current_tenant_member,
    require_permission,
)
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

router = APIRouter(
    prefix="/sms-ingestion",
    tags=["SMS Ingestion"],
)


@router.post(
    "/messages",
    response_model=SmsIngestResponse,
    status_code=status.HTTP_201_CREATED,
)
def receive_sms(
    payload: SmsIngestRequest,
    db: Session = Depends(get_db),
    membership=Depends(get_current_tenant_member),
    _permission=Depends(require_permission("sms.ingest")),
):
    return ingest_sms(
        db,
        tenant_id=membership.tenant_id,
        network=payload.network,
        raw_body=payload.raw_body,
    )


@router.get(
    "/messages/{message_id}",
    response_model=SmsIngestResponse,
)
def read_sms_message(
    message_id: UUID,
    db: Session = Depends(get_db),
    membership=Depends(get_current_tenant_member),
    _permission=Depends(require_permission("sms.read")),
):
    message = get_sms_message(
        db,
        tenant_id=membership.tenant_id,
        message_id=message_id,
    )

    if message is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="SMS message not found.",
        )

    return message
