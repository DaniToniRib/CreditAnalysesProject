import logging

from app.connectors.sap_service_layer import SAPServiceLayerClient
from app.connectors.serasa_client import SerasaClient
from app.database import SessionLocal
from app.models.customer import Customer
from app.models.financial import Order
from app.services.customer_sync import sync_customer_master_data
from app.services.history_sync import sync_customer_financial_history
from app.services.order_analysis import analyze_order, record_score_and_limit
from app.services.order_ingestion import poll_new_sap_orders
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


@celery_app.task(name="app.tasks.jobs.poll_new_orders_task")
def poll_new_orders_task() -> None:
    """Busca pedidos novos no SAP B1 e dispara a análise de crédito de cada um."""
    db = SessionLocal()
    sap_client = SAPServiceLayerClient()
    try:
        new_orders = poll_new_sap_orders(db, sap_client)
        for order in new_orders:
            analyze_order_task.delay(order.id)
        if new_orders:
            logger.info("%s pedido(s) novo(s) detectado(s) no SAP", len(new_orders))
    finally:
        sap_client.close()
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
                sync_customer_master_data(db, customer, sap_client)
                sync_customer_financial_history(db, customer, sap_client)
                serasa_query = get_or_query_serasa(db, customer, serasa_client)
                record_score_and_limit(db, customer, serasa_query)
                db.commit()
            except Exception:  # noqa: BLE001
                db.rollback()
                logger.exception(
                    "Falha ao reavaliar cliente %s na reavaliação periódica",
                    customer.sap_card_code,
                )
        db.commit()
    finally:
        sap_client.close()
        serasa_client.close()
        db.close()
