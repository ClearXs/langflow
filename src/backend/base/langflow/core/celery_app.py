from celery import Celery


def make_celery(app_name: str, config: str) -> Celery:
    celery_app = Celery(app_name)
    celery_app.config_from_object(config)
    celery_app.conf.task_routes = {"langflow.worker.tasks.*": {"queue": "langflow"}}
    return celery_app


celery_app = make_celery("langflow", "langflow.core.celeryconfig")

# Import tasks to register them with Celery
# This must be done after celery_app is created
from langflow.workers import document_tasks  # noqa: E402, F401
from langflow.tasks import knowledge_graph_tasks  # noqa: E402, F401
from langflow.tasks import lightrag_graph_tasks  # noqa: E402, F401
