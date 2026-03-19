from passlib.context import CryptContext
from itsdangerous import URLSafeTimedSerializer
from fastapi import Request
from sqlmodel import Session
from app.models import User
import os

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECRET_KEY = os.getenv("SECRET_KEY", "change-this-in-prod-please")
serializer = URLSafeTimedSerializer(SECRET_KEY)

SESSION_COOKIE = "stackd_session"
SESSION_MAX_AGE = 60 * 60 * 24 * 30  # 30 days
MIN_PASSWORD_LENGTH = 8


class NeedsAuthException(Exception):
    """Raised when a route requires auth and none is present."""
    pass


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def validate_password(password: str) -> Optional[str]:
    """Returns error string if invalid, None if valid."""
    if len(password) < MIN_PASSWORD_LENGTH:
        return f"Password must be at least {MIN_PASSWORD_LENGTH} characters"
    return None


def create_session_token(user_id: int) -> str:
    return serializer.dumps(user_id, salt="session")


def decode_session_token(token: str) -> int:
    return serializer.loads(token, salt="session", max_age=SESSION_MAX_AGE)


def require_user(request: Request, session: Session) -> User:
    """
    Call at the top of every protected route.
    Raises NeedsAuthException if not authenticated —
    handled globally in main.py with HTMX awareness.
    """
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        raise NeedsAuthException()
    try:
        user_id = decode_session_token(token)
    except Exception:
        raise NeedsAuthException()
    user = session.get(User, user_id)
    if not user:
        raise NeedsAuthException()
    return user


# Add Optional import at top
from typing import Optional