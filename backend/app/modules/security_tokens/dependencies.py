from typing import Annotated

from app.db.session import get_db
from app.modules.auth.dependencies import get_current_user
from app.modules.security_tokens.service import (
    verify_user_security_token,
)
from fastapi import Depends, Header
from sqlalchemy.orm import Session


def require_security_token(
    security_token: Annotated[
        str,
        Header(alias="X-Security-Token"),
    ],
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    verify_user_security_token(
        db,
        user_id=current_user.id,
        token=security_token,
    )

    return current_user
