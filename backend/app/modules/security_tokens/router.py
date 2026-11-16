from typing import Annotated

from app.db.session import get_db
from app.modules.auth.dependencies import get_current_user
from app.modules.security_tokens.schemas import (
    SecurityTokenResetRequest,
    SecurityTokenResetResponse,
    SecurityTokenVerifyRequest,
    SecurityTokenVerifyResponse,
)
from app.modules.security_tokens.service import (
    reset_user_security_token,
    verify_user_security_token,
)
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

router = APIRouter(
    prefix="/security-token",
    tags=["Security Token"],
)

DBSession = Annotated[Session, Depends(get_db)]


@router.post(
    "/verify",
    response_model=SecurityTokenVerifyResponse,
)
def verify_token(
    payload: SecurityTokenVerifyRequest,
    db: DBSession,
    current_user=Depends(get_current_user),
):
    verify_user_security_token(
        db,
        user_id=current_user.id,
        token=payload.token,
    )

    return SecurityTokenVerifyResponse(
        verified=True,
        message="Security Token verified successfully.",
    )


@router.post(
    "/reset",
    response_model=SecurityTokenResetResponse,
)
def reset_token(
    payload: SecurityTokenResetRequest,
    db: DBSession,
    current_user=Depends(get_current_user),
):
    new_token = reset_user_security_token(
        db,
        user_id=current_user.id,
        current_password=payload.current_password,
    )

    return SecurityTokenResetResponse(
        security_token=new_token,
        message=(
            "Security Token reset successfully. Save it securely; it will not be displayed again."
        ),
    )
