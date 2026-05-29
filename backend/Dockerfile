# Build context is the REPO ROOT (so we can include menu_data.py).
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1

WORKDIR /app/backend

# Dependencies first (layer cache)
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# App code + the root menu_data.py (v1 source of truth)
COPY backend/ /app/backend/
COPY menu_data.py /app/menu_data.py

EXPOSE 8000

# Seed (idempotent) then serve. DB must be reachable.
CMD ["sh", "-c", "python -m app.seed && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
