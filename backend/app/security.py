"""Security utilities: password hashing and JWT tokens."""
from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt

from app.config import settings

ALGORITHM = "HS256"
# bcrypt only considers the first 72 bytes of a password
MAX_PASSWORD_BYTES = 72


def hash_password(password: str) -> str:
    pw = password.encode("utf-8")[:MAX_PASSWORD_BYTES]
    return bcrypt.hashpw(pw, bcrypt.gensalt(rounds=12)).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8")[:MAX_PASSWORD_BYTES], hashed.encode("utf-8"))
    except Exception:  # noqa: BLE001
        return False


def create_access_token(subject: str, extra: dict | None = None) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
    except JWTError:
        return None


# ----------------------------------------------------------------------------
# Short-lived scoped tokens for PDF file links
#
# Browser tab navigation / <iframe> / <a href> cannot send an Authorization
# header, so citation links would otherwise hit a 401 JSON page. Instead the
# SPA mints a short-lived signed token for ONE document and appends it as a
# query parameter. Tokens expire quickly (FILE_TOKEN_TTL_SECONDS), carry no
# user identity, and are only valid for their document id.
# ----------------------------------------------------------------------------
FILE_TOKEN_PURPOSE = "doc-file"
FILE_TOKEN_TTL_SECONDS = 15 * 60  # 15 minutes


def create_file_token(document_id: int) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": "doc-file",
        "purpose": FILE_TOKEN_PURPOSE,
        "doc": document_id,
        "iat": now,
        "exp": now + timedelta(seconds=FILE_TOKEN_TTL_SECONDS),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def decode_file_token(token: str) -> int | None:
    """Return the document id the token was minted for, or None if invalid."""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
    except JWTError:
        return None
    if payload.get("purpose") != FILE_TOKEN_PURPOSE or payload.get("sub") != "doc-file":
        return None
    try:
        return int(payload["doc"])
    except (KeyError, TypeError, ValueError):
        return None
