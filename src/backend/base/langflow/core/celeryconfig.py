# celeryconfig.py
import os

from celery.schedules import crontab

langflow_redis_host = os.environ.get("LANGFLOW_REDIS_HOST") or "192.168.110.185"
langflow_redis_port = os.environ.get("LANGFLOW_REDIS_PORT") or "6379"
langflow_redis_password = os.environ.get("LANGFLOW_REDIS_PASSWORD") or "ImagDev@123"
# broker default user

if langflow_redis_host and langflow_redis_port:
    if langflow_redis_password:
        broker_url = f"redis://:{langflow_redis_password}@{langflow_redis_host}:{langflow_redis_port}/0"
        result_backend = f"redis://:{langflow_redis_password}@{langflow_redis_host}:{langflow_redis_port}/0"
    else:
        broker_url = f"redis://{langflow_redis_host}:{langflow_redis_port}/0"
        result_backend = f"redis://{langflow_redis_host}:{langflow_redis_port}/0"
else:
    # RabbitMQ
    mq_user = os.environ.get("RABBITMQ_DEFAULT_USER", "langflow")
    mq_password = os.environ.get("RABBITMQ_DEFAULT_PASS", "langflow")
    broker_url = os.environ.get("BROKER_URL", f"amqp://{mq_user}:{mq_password}@localhost:5672//")
    result_backend = os.environ.get("RESULT_BACKEND", "redis://localhost:6379/0")
# tasks should be json or pickle
accept_content = ["json", "pickle"]

# Celery Beat schedule for periodic tasks
beat_schedule = {
    "sync-all-connectors": {
        "task": "langflow.workers.sync_all_connectors",
        "schedule": crontab(minute="*/30"),  # Run every 30 minutes
        "options": {"queue": "langflow"},
    },
}
