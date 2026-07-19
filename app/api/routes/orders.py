from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db, verify_api_key
from app.models.customer import Customer
from app.models.financial import Order, OrderStatus
from app.schemas.order import (
    NewOrderIn,
    OrderAnalysisOut,
    OrderDecisionIn,
    OrderPendingOut,
)
from app.services.order_review import OrderNotReviewableError, apply_manual_decision
from app.tasks.jobs import analyze_order_task

router = APIRouter(prefix="/orders", tags=["orders"], dependencies=[Depends(verify_api_key)])

# Pedidos que ainda precisam de alguma ação (análise ou decisão humana)
PENDING_STATUSES = (
    OrderStatus.EM_ANALISE,
    OrderStatus.APROVADO_COM_RESSALVA,
    OrderStatus.BLOQUEADO,
)


def _get_or_create_customer(db: Session, card_code: str) -> Customer:
    customer = db.query(Customer).filter(Customer.sap_card_code == card_code).one_or_none()
    if customer is None:
        # Nome real será preenchido no próximo sync com o SAP (BusinessPartners);
        # aqui só garantimos que o pedido tenha um cliente para se vincular.
        customer = Customer(sap_card_code=card_code, name=card_code)
        db.add(customer)
        db.flush()
    return customer


@router.post("", response_model=OrderAnalysisOut, status_code=202)
def receive_new_order(payload: NewOrderIn, db: Session = Depends(get_db)) -> OrderAnalysisOut:
    """Cria um pedido manualmente e dispara a análise de crédito de forma
    assíncrona (Celery). O mecanismo principal de detecção de pedido novo é
    o polling periódico (`tasks.jobs.poll_new_orders_task`) — este endpoint é
    uma via alternativa (ex.: reprocessar um caso específico, outra integração).
    """
    existing = db.query(Order).filter(Order.sap_doc_entry == payload.sap_doc_entry).one_or_none()
    if existing is not None:
        raise HTTPException(status_code=409, detail="Pedido já registrado (sap_doc_entry duplicado)")

    customer = _get_or_create_customer(db, payload.sap_card_code)

    order = Order(
        customer_id=customer.id,
        sap_doc_entry=payload.sap_doc_entry,
        sap_doc_num=payload.sap_doc_num,
        order_date=payload.order_date,
        amount=payload.amount,
    )
    db.add(order)
    db.commit()
    db.refresh(order)

    analyze_order_task.delay(order.id)

    return OrderAnalysisOut.model_validate(order)


@router.get("/pending", response_model=list[OrderPendingOut])
def list_pending_orders(db: Session = Depends(get_db)) -> list[OrderPendingOut]:
    """Fila de pedidos que ainda precisam de análise ou decisão humana."""
    orders = (
        db.query(Order)
        .filter(Order.status.in_(PENDING_STATUSES))
        .order_by(Order.received_at.asc())
        .all()
    )
    return [
        OrderPendingOut(
            id=o.id,
            sap_card_code=o.customer.sap_card_code,
            customer_name=o.customer.name,
            sap_doc_num=o.sap_doc_num,
            amount=float(o.amount),
            total_consumption_at_analysis=(
                float(o.total_consumption_at_analysis)
                if o.total_consumption_at_analysis is not None
                else None
            ),
            credit_limit_at_analysis=(
                float(o.credit_limit_at_analysis)
                if o.credit_limit_at_analysis is not None
                else None
            ),
            status=o.status,
            analyzed_at=o.analyzed_at,
        )
        for o in orders
    ]


@router.post("/{order_id}/decision", response_model=OrderAnalysisOut)
def decide_order(
    order_id: int, payload: OrderDecisionIn, db: Session = Depends(get_db)
) -> OrderAnalysisOut:
    """Decisão humana sobre um pedido aprovado com ressalva ou bloqueado."""
    order = db.get(Order, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")

    try:
        order = apply_manual_decision(db, order, payload.approve, payload.reviewer, payload.notes)
    except OrderNotReviewableError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    return OrderAnalysisOut.model_validate(order)
