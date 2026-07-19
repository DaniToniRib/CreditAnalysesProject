from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.customer import Customer
from app.models.financial import Order
from app.schemas.order import NewOrderIn, OrderAnalysisOut
from app.tasks.jobs import analyze_order_task

router = APIRouter(prefix="/orders", tags=["orders"])


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
    """Recebido quando o SAP B1 cria um novo pedido de venda.

    Dispara a análise de crédito de forma assíncrona (Celery); o pedido
    fica com status `em_analise` até o worker concluir.
    """
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
