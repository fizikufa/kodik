"""Отдача HTML-страниц."""
from pathlib import Path
from fastapi import APIRouter
from fastapi.responses import FileResponse, RedirectResponse


router = APIRouter()
STATIC_DIR = Path(__file__).resolve().parents[2] / "static"


@router.get("/")
async def root():
    return RedirectResponse("/chat")


@router.get("/login")
async def login_page():
    return FileResponse(STATIC_DIR / "login.html")


@router.get("/chat")
async def chat_page():
    return FileResponse(STATIC_DIR / "chat.html")


@router.get("/admin")
async def admin_page():
    return FileResponse(STATIC_DIR / "admin.html")
