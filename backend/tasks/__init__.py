"""
Celery task queue setup for document processing.

This module initializes the Celery application and configures it
for handling document processing tasks.
"""

import logging
from celery import Celery
from backend.core.config import get_settings

logger = logging.getLogger(__name__)

# Get settings
settings = get_settings()

# Create Celery app
celery_app = Celery(
    "doclingflow",
    broker=settings.redis.broker_url,
    backend=settings.redis.result_backend,
    include=[
        "backend.tasks.ingestion",
        "backend.tasks.processing",
    ]
)

# Configure Celery
celery_app.conf.update(
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    
    # Worker settings
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    worker_disable_rate_limits=True,
    
    # Result settings
    result_expires=3600,  # 1 hour
    
    # Task routing
    task_routes={
        "backend.tasks.ingestion.*": {"queue": "ingestion"},
        "backend.tasks.processing.*": {"queue": "processing"},
    },
    
    # Retry settings
    task_default_retry_delay=60,  # 1 minute
    task_max_retries=3,
    
    # Monitoring
    worker_send_task_events=True,
    task_send_sent_event=True,
)

# Configure logging
celery_app.conf.update(
    worker_log_format="[%(asctime)s: %(levelname)s/%(processName)s] %(message)s",
    worker_task_log_format="[%(asctime)s: %(levelname)s/%(processName)s][%(task_name)s(%(task_id)s)] %(message)s",
)

logger.info("Celery app initialized successfully")


def get_celery_app() -> Celery:
    """Get the Celery app instance."""
    return celery_app
