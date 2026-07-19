from celery import Celery
from celery.schedules import crontab

from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "analise_credito",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.tasks.jobs"],
)

celery_app.conf.beat_schedule = {
    "reavaliacao-mensal-carteira": {
        "task": "app.tasks.jobs.recalculate_all_customers_task",
        # Todo dia 1 às 03:00 — reavalia score/limite de toda a base,
        # já que o comportamento de pagamento muda mesmo sem pedido novo
        "schedule": crontab(day_of_month=1, hour=3, minute=0),
    },
}
celery_app.conf.timezone = "America/Sao_Paulo"
