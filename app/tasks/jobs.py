import logging

from app.connectors.sap_service_layer import SAPServiceLayerClient
from app.connectors.serasa_client import SerasaClient
from app.database import SessionLocal
from app.models.customer import Customer
from app.models.financial import Order
from app.services.credit_limit import RULE_VERSION, calculate_credit_limit
from app.services.history_sync import sync_customer_financial_history
from app.services.order_analysis import analyze_order
from app.services.scoring import calculate_score
from app.services.serasa_service import get_or_query_serasa
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.jobs.analyze_order_task", bind=True, max_retries=3)
def analyze_order_task(self, order_id: int) -> None:
    db = SessionLocal()
    try:
        order = db.get(Order, order_id)
        if order is None:
            logger.warning("Order %s não encontrado para análise", order_id)
            return
        analyze_order(db, order)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Falha ao analisar pedido %s", order_id)
        raise self.retry(exc=exc, countdown=60) from exc
    finally:
        db.close()


@celery_app.task(name="app.tasks.jobs.recalculate_all_customers_task")
def recalculate_all_customers_task() -> None:
    """Reavaliação periódica de score/limite de toda a carteira de clientes."""
    db = SessionLocal()
    sap_client = SAPServiceLayerClient()
    serasa_client = SerasaClient()
    try:
        for customer in db.query(Customer).all():
            try:
                sync_customer_financial_history(db, customer, sap_client)
                serasa_query = get_or_query_serasa(db, customer, serasa_client)
                score_result = calculate_score(customer, serasa_query)
                calculate_credit_limit(customer, score_result.score)
                # O salvamento completo do histórico de score/limite segue o
                # mesmo padrão de `order_analysis.analyze_order`, sem o vínculo
                # com um pedido específico — reaproveitar aquela lógica aqui
                # ao consolidar (evitar duplicação de código antes de ter uso real).
            except Exception:  # noqa: BLE001
                logger.exception(
                    "Falha ao reavaliar cliente %s na reavaliação periódica",
                    customer.sap_card_code,
                )
        db.commit()
    finally:
        sap_client.close()
        serasa_client.close()
        db.close()
