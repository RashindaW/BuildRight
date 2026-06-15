# Cloud deployment (GCP Cloud Run / AWS ECS)

The live demo runs free on Hugging Face Spaces. Moving to a major cloud is **config,
not a rewrite** — the same root `Dockerfile` (FastAPI serving the SPA single-origin on
port 8000) runs anywhere, and only `DATABASE_URL` + secrets change. The app already
supports **Postgres + pgvector** via SQLAlchemy/Alembic, so production gets real
persistence and vector search.

## What changes vs HF
| Concern | HF demo | Cloud (prod) |
|---|---|---|
| DB | ephemeral SQLite (seeded at start) | **managed Postgres + pgvector** (Cloud SQL / RDS / Neon) via `DATABASE_URL` |
| Secrets | Space secrets | **Secret Manager** (GCP) / **SSM/Secrets Manager** (AWS) |
| Images | picsum + committed Pexels JSON | same, or move to **object storage + CDN** (GCS/S3 + CloudFront) |
| Scaling | one Space | autoscaling + health checks (`/health/ready`) |
| Seed | at container start | run **migrations** in a release step, seed once (not per cold start) |

## GCP — Cloud Run
```bash
PROJECT=my-proj REGION=us-central1 IMAGE=us-central1-docker.pkg.dev/$PROJECT/app/smarthandyman

# 1. Build + push (Cloud Build uses the root Dockerfile)
gcloud builds submit --tag $IMAGE

# 2. Managed Postgres + pgvector (Cloud SQL), then store secrets
echo -n "$DATABASE_URL"     | gcloud secrets create DATABASE_URL --data-file=-
echo -n "$ANTHROPIC_API_KEY"| gcloud secrets create ANTHROPIC_API_KEY --data-file=-
echo -n "$SECRET_KEY"       | gcloud secrets create SECRET_KEY --data-file=-

# 3. Deploy (port 8000; secrets mounted as env)
gcloud run deploy smarthandyman --image $IMAGE --region $REGION \
  --port 8000 --allow-unauthenticated --min-instances 0 --max-instances 5 \
  --set-secrets DATABASE_URL=DATABASE_URL:latest,ANTHROPIC_API_KEY=ANTHROPIC_API_KEY:latest,SECRET_KEY=SECRET_KEY:latest \
  --set-env-vars ENVIRONMENT=production,IMAGE_PROVIDER=placeholder
```
For prod, set the container command to migrate-then-serve, or run
`alembic upgrade head && python -m app.seed` as a one-off Cloud Run Job before traffic.

## AWS — ECS / Fargate (sketch)
1. `docker build` → push to **ECR**.
2. **RDS Postgres** with the `vector` extension; put `DATABASE_URL` + keys in **Secrets Manager**.
3. **ECS Fargate** service, container port **8000**, behind an **ALB**; health check `/health/ready`.
4. Autoscale on CPU/requests; run migrations as a one-off task on deploy.

## Notes
- SSE streaming rules out pure-serverless edges; Cloud Run / ECS keep long-lived
  connections fine (the app already sends `X-Accel-Buffering: no`).
- `ENVIRONMENT=production` enables secure cookies (`SameSite=None; Secure`) — required
  behind HTTPS, which both platforms provide.
- CI gate before deploy: the 244 backend tests + `tsc` + `alembic check` (see `.github/workflows`).
