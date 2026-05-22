import os

bind = f"0.0.0.0:{os.getenv('PORT', '10000')}"
workers = 2
worker_class = "uvicorn.workers.UvicornWorker"
timeout = 60
graceful_timeout = 30
keepalive = 5
accesslog = "-"
errorlog = "-"
loglevel = "info"
