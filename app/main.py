"""FastAPI entry-point."""
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from sqlalchemy import select

from .auth import hash_password
from .config import settings
from .database import SessionLocal, init_db
from .models import User
from .routers import admin, auth, chat, pages


async def ensure_admin():
    """Создаёт начального админа, если его нет."""
    async with SessionLocal() as db:
        res = await db.execute(select(User).where(User.is_admin == True))  # noqa
        if res.scalar_one_or_none():
            return
        admin_user = User(
            username=settings.admin_username,
            password_hash=hash_password(settings.admin_password),
            is_admin=True,
            is_active=True,
            rpm_limit=120,
            monthly_budget=1000.0,
        )
        db.add(admin_user)
        await db.commit()
        print(f"[init] Создан админ: {settings.admin_username}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    os.makedirs("data", exist_ok=True)
    await init_db()
    await ensure_admin()
    yield


app = FastAPI(title="KodikRouter Chat Service", lifespan=lifespan)

app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(chat.router)
app.include_router(pages.router)
