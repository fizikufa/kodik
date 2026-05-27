"""Аутентификация: JWT + bcrypt."""
import warnings
warnings.filterwarnings("ignore", ".*error reading bcrypt version.*")

from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import jwt, JWTError
from passlib.context import CryptContext

from .config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    p = password.encode("utf-8")[:72]
    return pwd_context.hash(p)


def verify_password(plain: str, hashed: str) -> bool:
    try:
        p = plain.encode("utf-8")[:72]
        return pwd_context.verify(p, hashed)
    except Exception:
        return False


def create_access_token(user_id: int, is_admin: bool) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=settings.jwt_expire_hours)
    payload = {"sub": str(user_id), "adm": is_admin, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_alg)


def decode_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_alg])
    except JWTError:
        return None
