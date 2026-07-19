"""Aplica a decisão humana sobre um pedido em análise/ressalva/bloqueado.

Compartilhado entre a API protegida por API key (`api/routes/orders.py`) e
o painel HTML interno (`api/routes/dashboard.py`).
"""

from datetime import datetime

from sqlalchemy.orm import Session

from app.models.financial import Order, OrderStatus

REVIEWABLE_STATUSES = (OrderStatus.APROVADO_COM_RESSALVA, OrderStatus.BLOQUEADO)


class OrderNotReviewableError(Exception):
    pass


def apply_manual_decision(
    db: Session, order: Order, approve: bool, reviewer: str, notes: str | None = None
) -> Order:
    if order.status not in REVIEWABLE_STATUSES:
        raise OrderNotReviewableError(
            f"Pedido no status '{order.status.value}' não aceita decisão manual"
        )

    order.status = OrderStatus.APROVADO if approve else OrderStatus.REJEITADO
    order.reviewed_by = reviewer
    order.reviewed_at = datetime.utcnow()
    order.review_notes = notes

    db.commit()
    db.refresh(order)
    return order
