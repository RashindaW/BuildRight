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
# EMBEDDING_PROVIDER=hash → no model download. CATALOG_TARGET sizes the catalog.
# ENVIRONMENT=production → secure cookies + secret-key validation on the live HTTPS Space.
# USE_PLACEHOLDER_IMAGES=false → panel-curated per-TYPE product photos (committed
# type_images.json); types without a vetted photo automatically keep the branded SVG tile.
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 \
    EMBEDDING_PROVIDER=hash \
    CATALOG_TARGET=3000 \
    ENVIRONMENT=production \
    USE_PLACEHOLDER_IMAGES=false

WORKDIR /app/backend

# Backend deps (layer cache)
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Backend code + the root menu_data.py, and the built SPA where _mount_spa() looks
# for it (<repo root>/frontend/dist → /app/frontend/dist).
COPY backend/ /app/backend/
COPY menu_data.py /app/menu_data.py
# The policy/FAQ corpus. seed_kb resolves it at <repo root>/knowledge_base, which is
# /app here, so it MUST land at /app/knowledge_base. Without it the seed produced 0
# policy documents and every returns/warranty/shipping answer silently degraded to
# "contact customer service", while product search kept working.
COPY knowledge_base/ /app/knowledge_base/
COPY --from=frontend /fe/dist /app/frontend/dist

# Hugging Face routes to this port (see app_port in the Space README).
EXPOSE 8000

# Seed at STARTUP so runtime Space secrets take effect (ADMIN_PASSWORD, CATALOG_TARGET,
# IMAGE_PROVIDER, …). The heavy build steps (npm/pip) are already done in the image, and
# the seed is offline (hash embeddings) + idempotent. Then serve the SPA + API.
CMD ["sh", "-c", "python -m app.seed && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
