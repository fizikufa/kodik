"""Чат: CRUD чатов/сообщений, completion-запросы с лимитами, загрузка файлов."""
import json
from pathlib import Path
try:
    import tiktoken as _tiktoken
    _enc = _tiktoken.get_encoding("cl100k_base")
    def _count_tokens(s: str) -> int: return len(_enc.encode(s))
except Exception:
    def _count_tokens(s: str) -> int: return max(1, int(len(s.split()) * 1.3))

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..database import get_session
from ..deps import get_current_user
from ..kodik_client import KodikClient, get_kodik_credentials
from ..models import Chat, Message, SystemPreset, Usage, User
from ..rate_limiter import (
    check_limits, calculate_cost, get_usd_to_rub, get_usage_by_model,
    count_requests_last_minute, spent_this_month, total_requests,
)
from ..schemas import (
    ChatCreate, ChatOut, ChatUpdate, CompletionIn,
    MessageOut, PresetCreate, PresetOut,
)
from ..file_extractor import (
    extract_text, encode_image,
    MAX_FILE_SIZE, SUPPORTED_EXTENSIONS, IMAGE_EXTENSIONS, MAX_TEXT_CHARS,
)

router = APIRouter(prefix="/api/chat", tags=["chat"])


# ─── Chats CRUD ───
@router.get("/chats", response_model=list[ChatOut])
async def list_chats(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    res = await db.execute(
        select(Chat).where(Chat.user_id == user.id).order_by(Chat.updated_at.desc())
    )
    return res.scalars().all()


@router.post("/chats", response_model=ChatOut)
async def create_chat(
    body: ChatCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    chat = Chat(
        user_id=user.id, title=body.title, model=body.model,
        system_prompt=body.system_prompt or user.default_system_prompt,
    )
    db.add(chat)
    await db.commit()
    await db.refresh(chat)
    return chat


@router.patch("/chats/{chat_id}", response_model=ChatOut)
async def update_chat(
    chat_id: int, body: ChatUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    chat = await db.get(Chat, chat_id)
    if not chat or chat.user_id != user.id:
        raise HTTPException(404, "Не найден")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(chat, k, v)
    await db.commit()
    await db.refresh(chat)
    return chat


@router.delete("/chats/{chat_id}")
async def delete_chat(
    chat_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    chat = await db.get(Chat, chat_id)
    if not chat or chat.user_id != user.id:
        raise HTTPException(404, "Не найден")
    await db.delete(chat)
    await db.commit()
    return {"ok": True}


@router.get("/chats/{chat_id}/messages", response_model=list[MessageOut])
async def list_messages(
    chat_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    chat = await db.get(Chat, chat_id)
    if not chat or chat.user_id != user.id:
        raise HTTPException(404, "Не найден")
    res = await db.execute(
        select(Message).where(Message.chat_id == chat_id).order_by(Message.id)
    )
    return res.scalars().all()


# ─── File upload ───
@router.post("/upload-file")
async def upload_file(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
):
    ext = Path(file.filename).suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(400, f"Формат {ext} не поддерживается. Допустимые: {', '.join(sorted(SUPPORTED_EXTENSIONS))}")

    data = await file.read()
    if len(data) > MAX_FILE_SIZE:
        raise HTTPException(400, f"Файл слишком большой. Максимум {MAX_FILE_SIZE // 1024 // 1024} MB")

    if ext in IMAGE_EXTENSIONS:
        return encode_image(file.filename, data)

    try:
        text = await extract_text(file.filename, data)
    except Exception as e:
        raise HTTPException(422, f"Не удалось прочитать файл: {e}")

    if not text.strip():
        raise HTTPException(422, "Файл пустой или не содержит текста")

    truncated = False
    if len(text) > MAX_TEXT_CHARS:
        text = text[:MAX_TEXT_CHARS] + "\n\n[... файл обрезан — превышен лимит контекста]"
        truncated = True

    return {
        "type": "text",
        "filename": file.filename,
        "content": text,
        "chars": len(text),
        "truncated": truncated,
    }


# ─── Models proxy ───
@router.get("/models")
async def list_models(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    api_key, base_url = await get_kodik_credentials(db)
    if not api_key:
        raise HTTPException(500, "API-ключ KodikRouter не настроен")
    client = KodikClient(api_key, base_url)
    try:
        return await client.list_models()
    except Exception as e:
        raise HTTPException(502, f"Ошибка KodikRouter: {e}")


# ─── Completion ───
def _extract_cost(chunk_or_resp: dict) -> float:
    """Возвращает стоимость в USD из ответа KodikRouter."""
    usage = chunk_or_resp.get("usage") or {}
    return float(
        usage.get("cost") or usage.get("total_cost") or chunk_or_resp.get("cost") or 0.0
    )


def _build_user_message(content: str, attachments: list) -> dict:
    """Формирует сообщение с вложениями в формат OpenAI content-array."""
    if not attachments:
        return {"role": "user", "content": content}

    # Собираем текстовые вложения в тело сообщения
    text_parts = content
    for att in attachments:
        if att.type == "text":
            text_parts += f"\n\n--- Файл: {att.filename} ---\n{att.content}"

    parts = [{"type": "text", "text": text_parts}]

    # Картинки отдельными блоками
    for att in attachments:
        if att.type == "image":
            parts.append({
                "type": "image_url",
                "image_url": {"url": f"data:{att.media_type};base64,{att.data}"},
            })

    return {"role": "user", "content": parts}


@router.post("/completion")
async def completion(
    body: CompletionIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    chat = await db.get(Chat, body.chat_id)
    if not chat or chat.user_id != user.id:
        raise HTTPException(404, "Чат не найден")

    ok, err = await check_limits(db, user)
    if not ok:
        raise HTTPException(429, err)

    api_key, base_url = await get_kodik_credentials(db)
    if not api_key:
        raise HTTPException(500, "API-ключ KodikRouter не настроен")

    # Сохраняем сообщение пользователя (только текст в БД)
    user_msg = Message(chat_id=chat.id, role="user", content=body.content, model=chat.model)
    db.add(user_msg)

    # Собираем историю
    res = await db.execute(
        select(Message).where(Message.chat_id == chat.id).order_by(Message.id)
    )
    history = res.scalars().all()

    messages = []
    if chat.system_prompt:
        messages.append({"role": "system", "content": chat.system_prompt})
    for m in history:
        messages.append({"role": m.role, "content": m.content})

    # Последнее сообщение — с вложениями
    messages.append(_build_user_message(body.content, body.attachments))

    payload = {
        "model": chat.model,
        "messages": messages,
        "temperature": body.temperature,
        "max_tokens": body.max_tokens,
    }

    await db.commit()
    client = KodikClient(api_key, base_url)

    # ────────── Non-stream ──────────
    if not body.stream:
        try:
            resp = await client.chat_completion(payload)
        except Exception as e:
            raise HTTPException(502, f"KodikRouter: {e}")

        content = resp["choices"][0]["message"]["content"]
        usage = resp.get("usage", {})
        pt = int(usage.get("prompt_tokens", 0))
        ct = int(usage.get("completion_tokens", 0))
        cost = _extract_cost(resp)
        # Если usage не пришёл в стриме — считаем токены сами
        if pt == 0:
            pt = _count_tokens(payload.get("messages","") if isinstance(payload.get("messages"), str) else " ".join(m.get("content","") if isinstance(m.get("content"), str) else "" for m in payload.get("messages", [])))
        if ct == 0:
            ct = _count_tokens(final_text)
        if cost == 0.0:
            cost = await calculate_cost(db, chat.model, pt, ct)
        else:
            rate = await get_usd_to_rub(db)
            cost = round(cost * rate, 6)

        assistant_msg = Message(
            chat_id=chat.id, role="assistant", content=content, model=chat.model,
            prompt_tokens=pt, completion_tokens=ct, cost_usd=cost,
        )
        db.add(assistant_msg)
        db.add(Usage(
            user_id=user.id, model=chat.model,
            prompt_tokens=pt, completion_tokens=ct, cost_usd=cost,
        ))
        await db.commit()
        return {"content": content, "prompt_tokens": pt, "completion_tokens": ct, "cost_usd": cost}

    # ────────── Stream ──────────
    async def stream_gen():
        final_text = ""
        pt = ct = 0
        cost = 0.0
        try:
            async for chunk in client.chat_completion_stream(payload):
                piece = (chunk.get("choices") or [{}])[0].get("delta", {}).get("content") or ""
                if piece:
                    final_text += piece
                    yield f"data: {json.dumps({'delta': piece})}\n\n"
                if chunk.get("usage"):
                    u = chunk["usage"]
                    pt = int(u.get("prompt_tokens", pt))
                    ct = int(u.get("completion_tokens", ct))
                    cost = _extract_cost(chunk) or cost
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
            yield "data: [DONE]\n\n"
            return

        # Fallback токены из текста если usage не пришёл
        if pt == 0:
            msgs = payload.get("messages", [])
            src = " ".join(m.get("content", "") if isinstance(m.get("content"), str) else "" for m in msgs)
            pt = _count_tokens(src)
        if ct == 0:
            ct = _count_tokens(final_text)

        # Конвертация: если cost пришёл от KodikRouter (USD) — умножаем на курс
        # если 0 — считаем по таблице цен (уже в рублях)
        if cost == 0.0:
            cost = await calculate_cost(db, chat.model, pt, ct)
        else:
            rate = await get_usd_to_rub(db)
            cost = round(cost * rate, 6)

        try:
            assistant_msg = Message(
                chat_id=chat.id, role="assistant", content=final_text, model=chat.model,
                prompt_tokens=pt, completion_tokens=ct, cost_usd=cost,
            )
            db.add(assistant_msg)
            db.add(Usage(
                user_id=user.id, model=chat.model,
                prompt_tokens=pt, completion_tokens=ct, cost_usd=cost,
            ))
            await db.commit()
        except Exception:
            await db.rollback()

        yield f"data: {json.dumps({'done': True, 'prompt_tokens': pt, 'completion_tokens': ct, 'cost_usd': cost})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(stream_gen(), media_type="text/event-stream")


# ─── Presets ───
@router.get("/presets", response_model=list[PresetOut])
async def list_presets(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    res = await db.execute(
        select(SystemPreset).where(SystemPreset.user_id == user.id).order_by(SystemPreset.id)
    )
    return res.scalars().all()


@router.post("/presets", response_model=PresetOut)
async def create_preset(
    body: PresetCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    p = SystemPreset(user_id=user.id, name=body.name, content=body.content)
    db.add(p)
    await db.commit()
    await db.refresh(p)
    return p


@router.delete("/presets/{preset_id}")
async def delete_preset(
    preset_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    p = await db.get(SystemPreset, preset_id)
    if not p or p.user_id != user.id:
        raise HTTPException(404, "Не найден")
    await db.delete(p)
    await db.commit()
    return {"ok": True}


# ─── Личная статистика ───
@router.get("/me/usage")
async def my_usage(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    return {
        "rpm_limit": user.rpm_limit,
        "monthly_budget": user.monthly_budget,
        "requests_last_minute": await count_requests_last_minute(db, user.id),
        "spent_this_month": await spent_this_month(db, user.id),
        "total_requests": await total_requests(db, user.id),
        "default_system_prompt": user.default_system_prompt,
        "by_model": await get_usage_by_model(db, user.id),
    }

