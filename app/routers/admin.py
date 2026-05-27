from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta

from ..deps import get_current_admin
from ..database import get_session
from ..models import User, ModelPricing, Usage
from ..schemas import UserCreate, UserUpdate, ModelPricingCreate, ModelPricingUpdate, SettingsUpdate

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/stats")
async def get_stats(db: AsyncSession = Depends(get_session), _: User = Depends(get_current_admin)):
    total_users = (await db.execute(select(func.count()).select_from(User))).scalar()
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    active_users = (await db.execute(
        select(func.count(func.distinct(Usage.user_id))).where(Usage.created_at >= thirty_days_ago)
    )).scalar()
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    requests_today = (await db.execute(
        select(func.count()).select_from(Usage).where(Usage.created_at >= today_start)
    )).scalar()
    month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    revenue_month = (await db.execute(
        select(func.sum(Usage.cost_usd)).where(Usage.created_at >= month_start)
    )).scalar() or 0.0
    return {
        "total_users": total_users,
        "active_users": active_users,
        "requests_today": requests_today,
        "revenue_month": round(float(revenue_month), 2),
    }


@router.get("/usage")
async def get_usage(
    limit: int = Query(50, le=500), offset: int = 0,
    db: AsyncSession = Depends(get_session), _: User = Depends(get_current_admin),
):
    res = await db.execute(
        select(Usage, User.username)
        .join(User, User.id == Usage.user_id)
        .order_by(Usage.created_at.desc())
        .limit(limit).offset(offset)
    )
    rows = res.all()
    return [
        {**{c.name: getattr(row.Usage, c.name) for c in Usage.__table__.columns},
         "username": row.username}
        for row in rows
    ]


@router.get("/users")
async def list_users(
    limit: int = Query(1000, le=5000), offset: int = 0,
    db: AsyncSession = Depends(get_session), _: User = Depends(get_current_admin),
):
    res = await db.execute(select(User).order_by(User.id).limit(limit).offset(offset))
    users = res.scalars().all()
    total = (await db.execute(select(func.count()).select_from(User))).scalar()
    return {"items": [_user_dict(u) for u in users], "total": total}


@router.post("/users")
async def create_user(
    body: UserCreate,
    db: AsyncSession = Depends(get_session), _: User = Depends(get_current_admin),
):
    from ..auth import hash_password
    existing = (await db.execute(select(User).where(User.username == body.username))).scalar_one_or_none()
    if existing:
        raise HTTPException(400, "Пользователь уже существует")
    user = User(
        username=body.username,
        password_hash=hash_password(body.password),
        is_admin=(getattr(body, "role", "user") == "admin"),
        monthly_budget=getattr(body, "daily_budget", None) or getattr(body, "monthly_budget", 5.0) or 5.0,
        rpm_limit=getattr(body, "rpm_limit", None) or 20,
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return _user_dict(user)


@router.patch("/users/{user_id}")
async def update_user(
    user_id: int, body: UserUpdate,
    db: AsyncSession = Depends(get_session), _: User = Depends(get_current_admin),
):
    res = await db.execute(select(User).where(User.id == user_id))
    user = res.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "Пользователь не найден")
    data = body.dict(exclude_unset=True)
    if "password" in data:
        from ..auth import hash_password
        user.password_hash = hash_password(data.pop("password"))
    if "role" in data:
        user.is_admin = (data.pop("role") == "admin")
    if "email" in data:
        data.pop("email")
    if "balance" in data:
        user.monthly_budget = data.pop("balance")
    if "daily_budget" in data:
        user.monthly_budget = data.pop("daily_budget")
    for k, v in data.items():
        if hasattr(user, k):
            setattr(user, k, v)
    await db.commit()
    await db.refresh(user)
    return _user_dict(user)


def _user_dict(u: User) -> dict:
    return {
        "id": u.id,
        "email": u.username,
        "username": u.username,
        "role": "admin" if u.is_admin else "user",
        "balance": float(u.monthly_budget or 0),
        "is_active": u.is_active,
        "rpm_limit": u.rpm_limit,
        "daily_budget": float(u.monthly_budget or 0),
        "created_at": u.created_at.isoformat() if u.created_at else None,
    }


@router.get("/pricing")
async def list_pricing(
    limit: int = Query(1000, le=5000), offset: int = 0,
    db: AsyncSession = Depends(get_session), _: User = Depends(get_current_admin),
):
    res = await db.execute(select(ModelPricing).order_by(ModelPricing.model).limit(limit).offset(offset))
    items = res.scalars().all()
    total = (await db.execute(select(func.count()).select_from(ModelPricing))).scalar()
    return {"items": [_pricing_dict(p) for p in items], "total": total}


@router.post("/pricing")
async def create_pricing(
    body: ModelPricingCreate,
    db: AsyncSession = Depends(get_session), _: User = Depends(get_current_admin),
):
    existing = (await db.execute(select(ModelPricing).where(ModelPricing.model == body.model))).scalar_one_or_none()
    if existing:
        raise HTTPException(400, "Модель уже существует")
    kwargs = {
        "model": body.model,
        "input_price_per_1m": body.input_price_per_1m,
        "output_price_per_1m": body.output_price_per_1m,
    }
    if body.cache_read_price_per_1m is not None and hasattr(ModelPricing, "cache_read_price_per_1m"):
        kwargs["cache_read_price_per_1m"] = body.cache_read_price_per_1m
    p = ModelPricing(**kwargs)
    db.add(p)
    await db.commit()
    await db.refresh(p)
    return _pricing_dict(p)


@router.patch("/pricing/{pricing_id}")
async def update_pricing(
    pricing_id: int, body: ModelPricingUpdate,
    db: AsyncSession = Depends(get_session), _: User = Depends(get_current_admin),
):
    res = await db.execute(select(ModelPricing).where(ModelPricing.id == pricing_id))
    p = res.scalar_one_or_none()
    if not p:
        raise HTTPException(404, "Запись не найдена")
    for k, v in body.dict(exclude_unset=True).items():
        if hasattr(p, k):
            setattr(p, k, v)
    if hasattr(p, "updated_at"):
        p.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(p)
    return _pricing_dict(p)


@router.delete("/pricing/{pricing_id}", status_code=204)
async def delete_pricing(
    pricing_id: int,
    db: AsyncSession = Depends(get_session), _: User = Depends(get_current_admin),
):
    res = await db.execute(select(ModelPricing).where(ModelPricing.id == pricing_id))
    p = res.scalar_one_or_none()
    if not p:
        raise HTTPException(404, "Запись не найдена")
    await db.delete(p)
    await db.commit()


def _pricing_dict(p: ModelPricing) -> dict:
    cache = getattr(p, "cache_read_price_per_1m", None)
    return {
        "id": p.id,
        "model": p.model,
        "input_price_per_1m": float(p.input_price_per_1m or 0),
        "output_price_per_1m": float(p.output_price_per_1m or 0),
        "cache_read_price_per_1m": float(cache) if cache else None,
        "updated_at": getattr(p, "updated_at", None) and p.updated_at.isoformat(),
    }


@router.get("/settings")
async def get_settings(db: AsyncSession = Depends(get_session), _: User = Depends(get_current_admin)):
    from ..models import AppSetting
    res = await db.execute(select(AppSetting))
    rows = res.scalars().all()
    return {r.key: r.value for r in rows}


@router.post("/settings")
async def save_settings(
    body: SettingsUpdate,
    db: AsyncSession = Depends(get_session), _: User = Depends(get_current_admin),
):
    from ..models import AppSetting
    for key, val in body.dict(exclude_none=True).items():
        res = await db.execute(select(AppSetting).where(AppSetting.key == key))
        setting = res.scalar_one_or_none()
        if setting:
            setting.value = str(val)
        else:
            db.add(AppSetting(key=key, value=str(val)))
    await db.commit()
    return {"ok": True}


@router.post("/change-password")
async def change_password(
    body: dict,
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_session),
):
    from ..auth import hash_password
    if not body.get("password"):
        raise HTTPException(400, "Пароль не может быть пустым")
    current_user.password_hash = hash_password(body["password"])
    await db.commit()
    return {"ok": True}
