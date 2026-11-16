import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import jwt
from pwdlib import PasswordHash

from app.core.config import settings

password_hash = PasswordHash.recommended()
JWT_ALGORITHM = "HS256"

"VeroJOsNtandu20EMACAg"


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return password_hash.verify(plain_password, hashed_password)


def create_access_token(
    subject: str,
    session_id: UUID,
    identity_type: str = "user",
    expires_minutes: int | None = None,
) -> str:
    now = datetime.now(UTC)
    duration = settings.ACCESS_TOKEN_EXPIRE_MINUTES if expires_minutes is None else expires_minutes

    payload = {
        "sub": subject,
        "sid": str(session_id),
        "jti": str(uuid4()),
        "type": "access",
        "identity_type": identity_type,
        "iat": now,
        "exp": now + timedelta(minutes=duration),
    }

    return jwt.encode(
        payload,
        settings.SECRET_KEY.get_secret_value(),
        algorithm=JWT_ALGORITHM,
    )


def decode_access_token(token: str) -> dict:
    payload = jwt.decode(
        token,
        settings.SECRET_KEY.get_secret_value(),
        algorithms=[JWT_ALGORITHM],
        options={
            "require": [
                "exp",
                "iat",
                "sub",
                "sid",
                "jti",
                "type",
                "identity_type",
            ]
        },
    )

    if payload.get("type") != "access":
        raise jwt.InvalidTokenError("Invalid token type")

    if payload.get("identity_type") not in {"user", "platform_user"}:
        raise jwt.InvalidTokenError("Invalid identity type")

    return payload


def generate_refresh_token() -> str:
    return secrets.token_urlsafe(64)


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def generate_security_token() -> str:
    return f"{secrets.randbelow(100000):05d}"


def hash_security_token(token: str) -> str:
    return password_hash.hash(token)


def verify_security_token(token: str, hashed_token: str) -> bool:
    if len(token) != 5 or not token.isdigit():
        return False

    return password_hash.verify(token, hashed_token)


def generate_random_token() -> str:
    return secrets.token_urlsafe(32)


def hash_random_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
