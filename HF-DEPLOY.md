# Deploy BuildRight to Hugging Face Spaces (free)

The whole app runs as **one free Docker Space** — FastAPI serves the built React SPA
single-origin, with the catalog baked into the image at build time. All tooling is free;
only Anthropic is paid (your key).

## 1. Create the Space
1. Go to **https://huggingface.co/new-space** (sign in / sign up — free).
2. **Space name:** `buildright` (or anything). **License:** your choice.
3. **SDK:** select **Docker** → **Blank**.
4. **Hardware:** **CPU basic** (free). Create the Space.

## 2. Push this repo to the Space
The Space is a git repo. From this project root:

```bash
# one-time: add the Space as a remote (replace <user>/<space>)
git remote add space https://huggingface.co/spaces/<user>/buildright
git push space HEAD:main
```
> HF builds the **root `Dockerfile`** automatically. The YAML block at the top of
> `README.md` (`sdk: docker`, `app_port: 8000`) tells HF how to run it.
> A Hugging Face **access token** is used as the git password (Settings → Access Tokens, write).

## 3. Set the secrets (Space → Settings → Variables and secrets → New secret)
Add these as **runtime secrets** (never commit them):

| Secret | Value | Notes |
|---|---|---|
| `ANTHROPIC_API_KEY` | `sk-ant-...` | required — chat / vision / router |
| `SECRET_KEY` | a 32+ char random string | required (prod validator enforces strength) |
| `STT_PROVIDER` | `groq` | enables voice |
| `STT_API_KEY` | `gsk_...` | free Groq Whisper key |
| `UNSPLASH_ACCESS_KEY` | your Unsplash key | optional — real product photos |
| `IMAGE_PROVIDER` | `unsplash` | only if you set the Unsplash key |
| `STRIPE_SECRET_KEY` / `STRIPE_PUBLISHABLE_KEY` | `sk_test_...` / `pk_test_...` | optional — test-mode payments + refunds |

`ENVIRONMENT=production` and port 8000 are already baked into the image; CORS is same-origin.

## 4. Done
HF builds (~3–5 min) and serves at `https://<user>-buildright.hf.space`. Open it →
storefront with images, the chat assistant (router live), the 🎤 voice mic, image search,
and `/manager` → **AI Operations**.

## Notes
- **Persistence:** the free filesystem is **ephemeral** — the baked catalog is always present,
  but new orders/chat reset when the Space restarts/sleeps. That's fine for a demo. For
  persistence (still free): create a **Neon** or **Supabase** Postgres (with `pgvector`) and add
  `DATABASE_URL=postgresql+psycopg://...` as a secret (then run `alembic upgrade head` + seed once).
- **Catalog size:** the image bakes ~3,000 products for fast cold starts. For the full 10k,
  rebuild with `--build-arg CATALOG_TARGET=10000` (or set it in the Space's Dockerfile ARG).
- **Real images on HF:** after deploy, with `UNSPLASH_ACCESS_KEY` set, the picsum placeholders can
  be swapped for licensed photos by running `python -m app.seed.backfill_images` once.
- **Embeddings:** the image uses the deterministic `hash` provider so build + query stay
  consistent and need no model download.

## Continuous improvement (edit → deploy → pull loop)

An HF Space is a git repo, so you get a two-way loop. **Source of truth = your local/GitHub
repo; HF is a deploy target.**

**Automatic (recommended):** the GitHub Action `.github/workflows/deploy-hf.yml` mirrors the repo
to the Space on every push to `main`, and HF rebuilds + redeploys. One-time setup:
- GitHub → Settings → Secrets and variables → Actions:
  - Secret **`HF_TOKEN`** = a Hugging Face **write** token (hf.co/settings/tokens)
  - Variable **`HF_SPACE`** = `<user>/<space>` (e.g. `rashi/buildright`)
- Then: edit code → commit → push to `main` → it's live in ~3–5 min. (Or click **Run workflow**.)

**Manual** (any branch), via `scripts/hf.sh`:
```bash
export HF_SPACE=<user>/<space>
export HF_TOKEN=hf_xxx          # write token (push only)
./scripts/hf.sh push            # deploy current branch -> Space (HF rebuilds)
./scripts/hf.sh pull            # bring HF-web-editor edits back down
```

**Pulling from HF:** if you tweak something in the HF web editor (README, a config), run
`./scripts/hf.sh pull` (or `git pull space main`) to bring it local **before** your next push,
so the mirror doesn't clobber it.

**What a redeploy resets:** each deploy rebuilds the image, which **re-seeds the baked catalog** —
so runtime data (orders/chat placed on the live site) resets on redeploy. Code/UI/prompt changes
persist (they're in the image). For data that survives redeploys, use the free Neon/Supabase
`DATABASE_URL` (see Notes above) — then the DB lives outside the container.

## Local smoke test (optional, needs Docker)
```bash
docker build -t buildright .
docker run -p 8000:8000 \
  -e ANTHROPIC_API_KEY=sk-ant-... \
  -e SECRET_KEY=$(python -c "import secrets;print(secrets.token_hex(24))") \
  -e ENVIRONMENT=production buildright
# open http://localhost:8000  →  /health/ready returns {"status":"ok"}
```
