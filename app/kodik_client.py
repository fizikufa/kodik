"""HTTP-клиент к KodikRouter API."""
import json
from typing import AsyncIterator
import httpx

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .config import settings
from .models import AppSetting


async def get_kodik_credentials(db: AsyncSession) -> tuple[str, str]:
    """Берёт API-ключ и base_url из БД, с фолбэком на env."""
    api_key = settings.kodik_api_key
    base_url = settings.kodik_base_url

    res = await db.execute(select(AppSetting))
    for s in res.scalars().all():
        if s.key == "kodik_api_key" and s.value:
            api_key = s.value
        elif s.key == "kodik_base_url" and s.value:
            base_url = s.value

    return api_key, base_url.rstrip("/")


class KodikClient:
    """Тонкая обёртка над httpx для KodikRouter API."""

    def __init__(self, api_key: str, base_url: str):
        self.api_key = api_key
        self.base_url = base_url

    @property
    def headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def list_models(self) -> list[dict]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.get(f"{self.base_url}/models", headers=self.headers)
            r.raise_for_status()
            data = r.json()
            return data.get("data", data) if isinstance(data, dict) else data

    async def chat_completion(self, payload: dict) -> dict:
        """Не-стриминговый запрос."""
        async with httpx.AsyncClient(timeout=300.0) as client:
            r = await client.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json={**payload, "stream": False},
            )
            if r.status_code >= 400:
                raise httpx.HTTPStatusError(r.text, request=r.request, response=r)
            return r.json()

    async def chat_completion_stream(self, payload: dict) -> AsyncIterator[dict]:
        """Стриминг через SSE. Yields dict-чанки."""
        async with httpx.AsyncClient(timeout=300.0) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json={**payload, "stream": True},
            ) as r:
                if r.status_code >= 400:
                    body = await r.aread()
                    raise httpx.HTTPStatusError(body.decode(), request=r.request, response=r)

                async for line in r.aiter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if data == "[DONE]":
                        break
                    try:
                        yield json.loads(data)
                    except json.JSONDecodeError:
                        continue
