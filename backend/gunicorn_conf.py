import os

bind = f"0.0.0.0:{os.getenv('PORT', '10000')}"
# Render Free Tier: 512MB RAM limit.
# Two workers = two full Python processes, each loading numpy/pandas/scipy/sklearn/hmmlearn.
# One uvicorn async worker is sufficient: concurrency is handled by asyncio + ThreadPoolExecutor.
# Set RENDER_WORKERS=2 if upgrading to a paid tier with more RAM.
workers = int(os.getenv("RENDER_WORKERS", "1"))

worker_class = "uvicorn.workers.UvicornWorker"
timeout = 60
graceful_timeout = 30
keepalive = 5
accesslog = "-"
errorlog = "-"
loglevel = "info"
