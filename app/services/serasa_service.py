"""Orquestra consultas à Serasa respeitando o cache/TTL configurado."""

from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.config import get_settings
from app.connectors.serasa_client import SerasaClient
from app.models.customer import Customer
from app.models.serasa import SerasaQuery

settings = get_settings()


def get_or_query_serasa(
    db: Session,
    customer: Customer,
    serasa_client: SerasaClient,
    order_id: int | None = None,
    force: bool = False,
) -> SerasaQuery:
    """Retorna a última consulta válida (dentro do TTL) ou realiza uma nova."""

    if not force:
        ttl_cutoff = datetime.utcnow() - timedelta(hours=settings.serasa_query_cache_ttl_hours)
        latest = max(
            (q for q in customer.serasa_queries if q.queried_at >= ttl_cutoff),
            key=lambda q: q.queried_at,
            default=None,
        )
        if latest is not None:
            return latest

    result = serasa_client.query_document(customer.cnpj_cpf)

    query = SerasaQuery(
        customer_id=customer.id,
        order_id=order_id,
        score=result.score,
        pefin_count=result.pefin_count,
        pefin_total_amount=result.pefin_total_amount,
        refin_count=result.refin_count,
        refin_total_amount=result.refin_total_amount,
        protests_count=result.protests_count,
        protests_total_amount=result.protests_total_amount,
        lawsuits_count=result.lawsuits_count,
        checks_returned_count=result.checks_returned_count,
        raw_response=result.raw_response,
    )
    db.add(query)
    db.commit()
    db.refresh(query)
    return query
