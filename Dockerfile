# Self-contained image for Hugging Face Spaces (Docker SDK) — one container serves
# the React SPA + the FastAPI API single-origin. Build context = repo root.
#
#   Stage 1 builds the frontend.  Stage 2 runs FastAPI and serves the built SPA.
#   The catalog + embeddings are SEEDED AT BUILD TIME (hash embeddings, no network,
#   no real keys) and baked into the image, so cold start is instant.
#
# Real API keys (Anthropic, Groq STT, Unsplash, Stripe) are provided at RUNTIME as
# Hugging Face Space secrets — never baked into the image.

# ---- Stage 1: build the React SPA -----------------------------------------
FROM node:20-slim AS frontend
WORKDIR /fe
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci || npm install
COPY frontend/ ./
RUN npm run build          # → /fe/dist

# ---- Stage 2: Python runtime ----------------------------------------------
FROM python:3.11-slim AS runtime
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 \
    EMBEDDING_PROVIDER=hash

WORKDIR /app/backend

# Backend deps (layer cache)
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Backend code + the root menu_data.py, and the built SPA where _mount_spa() looks
# for it (<repo root>/frontend/dist → /app/frontend/dist).
COPY backend/ /app/backend/
COPY menu_data.py /app/menu_data.py
COPY --from=frontend /fe/dist /app/frontend/dist

# Bake the catalog into the image. Dummy keys satisfy required config fields; the
# seed makes NO external calls and uses hash embeddings, so this is fully offline.
# Override catalog size with --build-arg CATALOG_TARGET=10000 (larger image/build).
ARG CATALOG_TARGET=3000
RUN ANTHROPIC_API_KEY=build-time-dummy \
    SECRET_KEY=build-time-seed-key-0123456789-abcdefghij \
    ENVIRONMENT=development \
    CATALOG_TARGET=${CATALOG_TARGET} \
    python -m app.seed

# Hugging Face routes to this port (see app_port in the Space README).
ENV ENVIRONMENT=production
EXPOSE 8000

# DB is already baked — just serve. Runtime secrets come from the Space settings.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
