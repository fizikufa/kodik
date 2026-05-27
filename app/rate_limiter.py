"""Проверка лимитов: RPM и месячный бюджет. Подсчёт стоимости через ModelPricing."""
from datetime import datetime, timedelta
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Usage, User, ModelPricing


async def count_requests_last_minute(db: AsyncSession, user_id: int) -> int:
    since = datetime.utcnow() - timedelta(minutes=1)
    q = select(func.count(Usage.id)).where(Usage.user_id == user_id, Usage.created_at >= since)
    return (await db.execute(q)).scalar_one()


async def spent_this_month(db: AsyncSession, user_id: int) -> float:
    now = datetime.utcnow()
    start = datetime(now.year, now.month, 1)
    q = select(func.coalesce(func.sum(Usage.cost_usd), 0.0)).where(
        Usage.user_id == user_id, Usage.created_at >= start
    )
    return float((await db.execute(q)).scalar_one() or 0.0)


async def total_requests(db: AsyncSession, user_id: int) -> int:
    q = select(func.count(Usage.id)).where(Usage.user_id == user_id)
    return (await db.execute(q)).scalar_one()


async def get_usage_by_model(db: AsyncSession, user_id: int) -> list[dict]:
    """Статистика по моделям для пользователя."""
    q = (
        select(
            Usage.model,
            func.count(Usage.id).label("requests"),
            func.coalesce(func.sum(Usage.prompt_tokens), 0).label("prompt_tokens"),
            func.coalesce(func.sum(Usage.completion_tokens), 0).label("completion_tokens"),
            func.coalesce(func.sum(Usage.cost_usd), 0.0).label("cost_usd"),
        )
        .where(Usage.user_id == user_id)
        .group_by(Usage.model)
        .order_by(func.sum(Usage.cost_usd).desc())
    )
    rows = (await db.execute(q)).all()
    return [
        {
            "model": r.model,
            "requests": r.requests,
            "prompt_tokens": r.prompt_tokens,
            "completion_tokens": r.completion_tokens,
            "cost_usd": float(r.cost_usd),
        }
        for r in rows
    ]


async def get_usd_to_rub(db: AsyncSession) -> float:
    """Читает курс из AppSetting, fallback на settings.usd_to_rub."""
    from .models import AppSetting
    from .config import settings as _settings
    res = await db.execute(select(AppSetting).where(AppSetting.key == "usd_to_rub"))
    row = res.scalar_one_or_none()
    try:
        return float(row.value) if row else _settings.usd_to_rub
    except Exception:
        return _settings.usd_to_rub


async def calculate_cost(
    db: AsyncSession, model: str, prompt_tokens: int, completion_tokens: int
) -> float:
    """
    Считает стоимость запроса через таблицу ModelPricing.
    Если модели нет в таблице — возвращает 0.0.
    """
    res = await db.execute(select(ModelPricing).where(ModelPricing.model == model))
    pricing = res.scalar_one_or_none()
    if not pricing:
        return 0.0
    cost = (prompt_tokens / 1_000_000) * pricing.input_price_per_1m
    cost += (completion_tokens / 1_000_000) * pricing.output_price_per_1m
    return round(cost, 8)


async def check_limits(db: AsyncSession, user: User) -> tuple[bool, str]:
    """Возвращает (ok, error_message)."""
    rpm = await count_requests_last_minute(db, user.id)
    if rpm >= user.rpm_limit:
        return False, f"Превышен RPM-лимит ({user.rpm_limit} req/min)."

    spent = await spent_this_month(db, user.id)
    if spent >= user.monthly_budget:
        return False, f"Исчерпан месячный бюджет: ${spent:.4f} / ${user.monthly_budget:.2f}."

    return True, ""
