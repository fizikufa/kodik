from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


# ─── Auth ───
class LoginIn(BaseModel):
    username: str
    password: str


# ─── Users ───
class UserOut(BaseModel):
    id: int
    username: str
    is_admin: bool
    is_active: bool
    rpm_limit: int
    monthly_budget: float
    default_system_prompt: str
    created_at: datetime

    class Config:
        from_attributes = True


class UserCreate(BaseModel):
    username: str = Field(min_length=2, max_length=64)
    password: str = Field(min_length=4)
    is_admin: bool = False
    rpm_limit: int = 20
    monthly_budget: float = 5.0
    role: Optional[str] = "user"
    daily_budget: Optional[float] = None


class UserUpdate(BaseModel):
    password: Optional[str] = None
    is_admin: Optional[bool] = None
    is_active: Optional[bool] = None
    rpm_limit: Optional[int] = None
    monthly_budget: Optional[float] = None
    default_system_prompt: Optional[str] = None
    role: Optional[str] = None
    email: Optional[str] = None
    balance: Optional[float] = None
    daily_budget: Optional[float] = None


class UserUsageOut(BaseModel):
    user_id: int
    username: str
    rpm_limit: int
    monthly_budget: float
    requests_last_minute: int
    spent_this_month: float
    total_requests: int


# ─── Chats ───
class ChatOut(BaseModel):
    id: int
    title: str
    model: str
    system_prompt: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ChatCreate(BaseModel):
    title: str
    model: str = "openai/gpt-4o-mini"
    system_prompt: str = ""


class ChatUpdate(BaseModel):
    title: Optional[str] = None
    model: Optional[str] = None
    system_prompt: Optional[str] = None


class MessageOut(BaseModel):
    id: int
    role: str
    content: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    cost_usd: float
    created_at: datetime

    class Config:
        from_attributes = True


# ─── File attachment ───
class FileAttachment(BaseModel):
    type: str                   # "text" | "image"
    filename: str
    content: str = ""           # для текстовых файлов
    data: str = ""              # base64 для картинок
    media_type: str = ""        # mime-тип картинки


# ─── Completion ───
class CompletionIn(BaseModel):
    chat_id: int
    content: str
    attachments: List[FileAttachment] = []
    temperature: float = 0.7
    max_tokens: int = 2048
    stream: bool = True


# ─── Presets ───
class PresetOut(BaseModel):
    id: int
    name: str
    content: str

    class Config:
        from_attributes = True


class PresetCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    content: str


# ─── App settings ───
class AppSettingsIn(BaseModel):
    kodik_api_key: Optional[str] = None
    kodik_base_url: Optional[str] = None


class AppSettingsOut(BaseModel):
    kodik_api_key_set: bool
    kodik_base_url: str


# ─── Model Pricing ───
class ModelPricingCreate(BaseModel):
    model: str = Field(min_length=1, max_length=128)
    prompt_cost_per_1k: float = 0.0
    completion_cost_per_1k: float = 0.0
    description: Optional[str] = None


class ModelPricingUpdate(BaseModel):
    prompt_cost_per_1k: Optional[float] = None
    completion_cost_per_1k: Optional[float] = None
    description: Optional[str] = None


class ModelPricingOut(BaseModel):
    model: str
    prompt_cost_per_1k: float
    completion_cost_per_1k: float
    description: Optional[str] = None

    class Config:
        from_attributes = True


class SettingsUpdate(BaseModel):
    kodik_api_key: Optional[str] = None
    kodik_base_url: Optional[str] = None
    default_rpm: Optional[int] = None
    default_daily_budget: Optional[float] = None
    usd_to_rub: Optional[float] = None
