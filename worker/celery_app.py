# worker/celery_app.py

import os
from celery import Celery
from dotenv import load_dotenv

# Load environment variables from .env file for local development
# Assumes .env file is in the project root or worker directory
load_dotenv()

# Use Redis as the broker and result backend for local development
# In production, this would likely point to AWS SQS and potentially another backend
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

app = Celery(
    "codeguardian_worker",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["worker.tasks"]  # List of modules to import when the worker starts
)

app.conf.update(
    task_serializer="json",
    accept_content=["json"],  # Ignore other content
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # Add other Celery configurations as needed
)

if __name__ == "__main__":
    # This allows running the worker directly for development
    # Command: celery -A worker.celery_app worker --loglevel=info
    app.start()

