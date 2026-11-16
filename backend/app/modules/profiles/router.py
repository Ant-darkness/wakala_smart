from typing import Annotated

from app.db.session import get_db
from app.modules.auth.dependencies import get_current_user
from app.modules.profiles.schemas import (
    ProfileResponse,
    ProfileSetupRequest,
    ProfileSetupResponse,
    ProfileUpdateRequest,
)
from app.modules.profiles.service import (
    setup_profile,
    update_profile,
)
from app.modules.security_tokens.dependencies import (
    require_security_token,
)
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

router = APIRouter(
    prefix="/profile",
    tags=["Profiles"],
)

DBSession = Annotated[Session, Depends(get_db)]


@router.post(
    "/setup",
    response_model=ProfileSetupResponse,
    status_code=status.HTTP_201_CREATED,
)
def complete_profile(
    payload: ProfileSetupRequest,
    db: DBSession,
    current_user=Depends(get_current_user),
):
    user, security_token = setup_profile(
        db,
        user_id=current_user.id,
        **payload.model_dump(),
    )

    return ProfileSetupResponse(
        profile=ProfileResponse.model_validate(user),
        security_token=security_token,
        message=(
            "Profile created. Save your Security Token securely. It will not be displayed again."
        ),
    )


@router.get(
    "/me",
    response_model=ProfileResponse,
)
def get_my_profile(
    current_user=Depends(get_current_user),
):
    return current_user


@router.patch(
    "/me",
    response_model=ProfileResponse,
)
def edit_my_profile(
    payload: ProfileUpdateRequest,
    db: DBSession,
    current_user=Depends(require_security_token),
):
    return update_profile(
        db,
        user_id=current_user.id,
        updates=payload.model_dump(exclude_unset=True),
    )
