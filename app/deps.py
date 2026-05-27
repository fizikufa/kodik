"""Зависимости FastAPI: текущий пользователь, проверка админа."""
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from .auth import decode_token
from .database import get_session
from .models import User


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_session),
) -> User:
    token = request.cookies.get("access_token")
    if not token:
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            token = auth[7:]
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Не авторизован")

    payload = decode_token(token)
    if not payload:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Невалидный токен")

    user = await db.get(User, int(payload["sub"]))
    if not user or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Пользователь не найден")
    return user


async def get_admin(user: User = Depends(get_current_user)) -> User:
    if not user.is_admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Только для администратора")
    return user


async def get_current_admin(current_user=None):
    from fastapi import Depends, HTTPException
    from .deps import get_current_user
    # placeholder — заменяется ниже
    pass

from fastapi import Depends, HTTPException

async def get_current_admin(current_user: "User" = Depends(get_current_user)) -> "User":
    if not getattr(current_user, "is_admin", False):
        raise HTTPException(status_code=403, detail="Доступ запрещён")
    return current_user
