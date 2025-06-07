import os

# Server socket
bind = f"0.0.0.0:{os.environ.get('WEBSITES_PORT', 8000)}"
backlog = 2048

# Worker processes
workers = 2
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000
timeout = 30
keepalive = 5

# Restart workers after this many requests, to help with memory leaks
max_requests = 1000
max_requests_jitter = 50

# Logging
loglevel = "info"
accesslog = "-"
errorlog = "-"

# Process naming
proc_name = "eduplatform-api"

# Application
wsgi_app = "app.main:app"
