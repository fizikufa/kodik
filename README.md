KodikRouter Chat
Веб-интерфейс для работы с языковыми моделями через KodikRouter — единый API-шлюз к OpenAI, Anthropic, DeepSeek, Google и другим провайдерам.
Возможности
💬 Чат с любой моделью через KodikRouter API
👥 Многопользовательский режим с регистрацией и авторизацией
🔐 Панель администратора: управление пользователями, тарифами, настройками
📎 Загрузка файлов: PDF, DOCX, XLSX, CSV, TXT, изображения
📊 Учёт использования: токены, стоимость в рублях, RPM-лимиты
💰 Гибкие тарифы: цены за 1M токенов для каждой модели
⚙️ Настройка курса USD→₽ прямо из админки
🌊 Streaming-ответы
🗂️ История чатов с поиском
📝 Системные промпты и пресеты
Стек
Компонент	Технология
Backend	FastAPI + SQLAlchemy (async)
База данных	SQLite (aiosqlite)
Аутентификация	JWT (python-jose)
Контейнеризация	Docker + Docker Compose
Frontend	Vanilla JS + marked.js + highlight.js
Быстрый старт
1. Клонируем репозиторий
```bash
git clone https://github.com/fizikufa/kodik.git
cd kodik
```
2. Создаём `.env`
```bash
cp .env.example .env
```
Заполните `.env`:
```env
SECRET_KEY=ваш-секретный-ключ-минимум-32-символа
KODIK_BASE_URL=https://api.kodik.ai
KODIK_API_KEY=sk-ваш-ключ
ADMIN_USERNAME=admin
ADMIN_PASSWORD=ваш-пароль
USD_TO_RUB=90.0
```
3. Запускаем
```bash
docker compose up -d --build
```
Приложение доступно на `http://localhost:8000`
4. Первый вход
Откройте `http://localhost:8000`
Войдите с данными из `.env` (`ADMIN_USERNAME` / `ADMIN_PASSWORD`)
Панель администратора: `http://localhost:8000/admin`
Структура проекта
```
kodik/
├── app/
│   ├── main.py              # Точка входа FastAPI
│   ├── config.py            # Настройки (pydantic-settings)
│   ├── models.py            # SQLAlchemy модели
│   ├── schemas.py           # Pydantic схемы
│   ├── database.py          # Подключение к БД
│   ├── deps.py              # Зависимости (auth)
│   ├── auth.py              # JWT авторизация
│   ├── kodik_client.py      # HTTP-клиент KodikRouter
│   ├── rate_limiter.py      # Лимиты и подсчёт стоимости
│   └── routers/
│       ├── auth.py          # /api/auth/*
│       ├── chat.py          # /api/chat/*
│       └── admin.py         # /api/admin/*
├── static/
│   ├── chat.html            # Интерфейс чата
│   ├── admin.html           # Панель администратора
│   └── login.html           # Страница входа
├── data/                    # SQLite БД и загруженные файлы (volume)
├── seed_pricing.py          # Скрипт заполнения цен моделей
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── .env.example
```
Управление
```bash
# Запустить
docker compose up -d

# Остановить
docker compose down

# Логи
docker logs kodik-webapp -f

# Обновить после изменений
docker compose up -d --build

# Заполнить/обновить цены моделей
docker exec kodik-webapp python seed_pricing.py
```
Настройка тарифов
В панели администратора → Тарифы моделей можно задать цену за 1M входящих и исходящих токенов для каждой модели в рублях.
Для массового обновления цен используйте скрипт:
```bash
docker exec kodik-webapp python seed_pricing.py
```
Лицензия
MIT
