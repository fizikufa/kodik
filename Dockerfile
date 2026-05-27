FROM python:3.12-slim
WORKDIR /app

# Обновляем pip и убираем предупреждение root
RUN pip install --upgrade pip --quiet

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    --root-user-action=ignore \
    --quiet

COPY . .
RUN mkdir -p data

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

