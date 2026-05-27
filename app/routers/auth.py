"""Login / logout / me."""
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import create_access_token, verify_password
from ..database import get_session
from ..deps import get_current_user
from ..models import User
from ..schemas import LoginIn, UserOut


router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login")
async def login(body: LoginIn, response: Response, db: AsyncSession = Depends(get_session)):
    res = await db.execute(select(User).where(User.username == body.username))
    user = res.scalar_one_or_none()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(401, "Неверный логин или пароль")
    if not user.is_active:
        raise HTTPException(403, "Учётная запись отключена")

    token = create_access_token(user.id, user.is_admin)
    response.set_cookie(
        "access_token", token,
        httponly=True, samesite="lax", max_age=60 * 60 * 24 * 7, path="/",
    )
    return {"ok": True, "is_admin": user.is_admin}


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("access_token", path="/")
    return {"ok": True}


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user)):
    return user
