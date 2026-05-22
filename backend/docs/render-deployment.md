# Render Deployment

## Service

- Runtime: Python
- Root directory: `backend`
- Build command: `pip install -r requirements.txt`
- Start command: `gunicorn main:app -k uvicorn.workers.UvicornWorker`
- Health check path: `/health`

## Required Environment Variables

- `ENVIRONMENT=production`
- `ALLOWED_ORIGINS=https://frontend-kuan-s-projects1.vercel.app`
- `CORS_WHITELIST=https://frontend-kuan-s-projects1.vercel.app`
- `FMP_API_KEY`
- `FINNHUB_API_KEY`
- `ALPHA_VANTAGE_API_KEY`
- `FIREBASE_SERVER_KEY`
- `FIREBASE_PROJECT_ID`

## Cache Refresh

`render.yaml` includes a cron job that runs:

```bash
python -m quant_engine.data_pipeline.scheduler
```

This refreshes quotes, histories, statements, and news for the constrained institutional universe after market close.
