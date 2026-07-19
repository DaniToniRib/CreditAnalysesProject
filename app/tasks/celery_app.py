from celery import Celery
from celery.schedules import crontab

from app.config import get_settings
from app.logging_config import configure_logging

settings = get_settings()
configure_logging()

celery_app = Celery(
    "analise_credito",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.tasks.jobs"],
)

celery_app.conf.beat_schedule = {
    "poll-novos-pedidos-sap": {
        "task": "app.tasks.jobs.poll_new_orders_task",
        # A cada 5 minutos — mecanismo principal de detecção de pedido novo,
        # já que o Service Layer não tem webhook confiável por padrão
        "schedule": 300.0,
    },
    "reavaliacao-mensal-carteira": {
        "task": "app.tasks.jobs.recalculate_all_customers_task",
        # Todo dia 1 às 03:00 — reavalia score/limite de toda a base,
        # já que o comportamento de pagamento muda mesmo sem pedido novo
        "schedule": crontab(day_of_month=1, hour=3, minute=0),
    },
}
celery_app.conf.timezone = "America/Sao_Paulo"
