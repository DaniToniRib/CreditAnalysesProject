"""Orquestra a análise completa de um novo pedido: Serasa -> Score -> Limite -> decisão."""

from sqlalchemy.orm import Session

from app.connectors.sap_service_layer import SAPServiceLayerClient
from app.connectors.serasa_client import SerasaClient
from app.models.credit_limit import CreditLimitHistory
from app.models.financial import Order, OrderStatus
from app.models.score import CreditScoreHistory
from app.services.consumption import total_consumption
from app.services.credit_limit import RULE_VERSION, calculate_credit_limit
from app.services.history_sync import sync_customer_financial_history
from app.services.scoring import calculate_score
from app.services.serasa_service import get_or_query_serasa


def analyze_order(db: Session, order: Order) -> Order:
    customer = order.customer

    sap_client = SAPServiceLayerClient()
    serasa_client = SerasaClient()
    try:
        sync_customer_financial_history(db, customer, sap_client)

        serasa_query = get_or_query_serasa(db, customer, serasa_client, order_id=order.id)

        score_result = calculate_score(customer, serasa_query)
        score_record = CreditScoreHistory(
            customer_id=customer.id,
            serasa_query_id=serasa_query.id,
            triggered_by_order_id=order.id,
            default_probability=score_result.default_probability,
            score=score_result.score,
            model_version=score_result.model_version,
            features_snapshot=score_result.features,
        )
        db.add(score_record)
        db.flush()

        credit_limit = calculate_credit_limit(customer, score_result.score)
        limit_record = CreditLimitHistory(
            customer_id=customer.id,
            score_history_id=score_record.id,
            calculated_limit=credit_limit,
            rule_version=RULE_VERSION,
        )
        db.add(limit_record)

        consumption = total_consumption(customer, float(order.amount))

        order.total_consumption_at_analysis = consumption
        order.credit_limit_at_analysis = credit_limit
        order.status = _decide_status(consumption, credit_limit, serasa_query)
        from datetime import datetime

        order.analyzed_at = datetime.utcnow()

        db.commit()
        db.refresh(order)
        return order
    finally:
        sap_client.close()
        serasa_client.close()


def _decide_status(consumption: float, credit_limit: float, serasa_query) -> OrderStatus:
    if consumption <= credit_limit:
        return OrderStatus.APROVADO

    # Estourou o limite calculado, mas sem restrições graves na Serasa:
    # aprova com ressalva para alçada humana decidir, em vez de bloquear direto
    has_severe_restriction = (
        serasa_query.protests_count > 0
        or serasa_query.lawsuits_count > 0
        or serasa_query.pefin_count > 0
    )
    if has_severe_restriction:
        return OrderStatus.BLOQUEADO
    return OrderStatus.APROVADO_COM_RESSALVA
