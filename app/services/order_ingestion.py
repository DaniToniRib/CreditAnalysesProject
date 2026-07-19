"""Ingestão de novos pedidos do SAP B1 via polling periódico do Service Layer.

O Service Layer não oferece webhooks confiáveis fora de configurações
avançadas (Notification Service), então o mecanismo principal de detecção
de pedido novo é este polling. O endpoint `POST /orders` continua
disponível como alternativa manual/para outras integrações.
"""

from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from app.connectors.sap_service_layer import SAPServiceLayerClient
from app.models.customer import Customer
from app.models.financial import Order
from app.models.sync_state import SyncState

SYNC_STATE_KEY = "last_order_sync_date"
# Primeira execução: olha alguns dias para trás para não perder pedidos
# criados antes do sistema estar no ar
DEFAULT_LOOKBACK_DAYS = 7


def _get_checkpoint(db: Session) -> date:
    state = db.get(SyncState, SYNC_STATE_KEY)
    if state is None:
        return date.today() - timedelta(days=DEFAULT_LOOKBACK_DAYS)
    return datetime.strptime(state.value, "%Y-%m-%d").date()


def _set_checkpoint(db: Session, value: date) -> None:
    state = db.get(SyncState, SYNC_STATE_KEY)
    if state is None:
        db.add(SyncState(key=SYNC_STATE_KEY, value=value.isoformat()))
    else:
        state.value = value.isoformat()


def _get_or_create_customer(db: Session, card_code: str) -> Customer:
    customer = db.query(Customer).filter(Customer.sap_card_code == card_code).one_or_none()
    if customer is None:
        # Nome real é preenchido no sync de dados cadastrais durante a análise
        # (ver `customer_sync.sync_customer_master_data`)
        customer = Customer(sap_card_code=card_code, name=card_code)
        db.add(customer)
        db.flush()
    return customer


def poll_new_sap_orders(db: Session, sap_client: SAPServiceLayerClient) -> list[Order]:
    """Busca pedidos novos no SAP desde o último checkpoint e cria os registros
    locais correspondentes, prontos para análise (não dispara a análise em si —
    isso é responsabilidade de quem chama, ver `tasks.jobs.poll_new_orders_task`)."""

    checkpoint = _get_checkpoint(db)
    raw_orders = sap_client.get_orders_since(checkpoint)

    doc_entries_seen = [raw["DocEntry"] for raw in raw_orders]
    existing_doc_entries = {
        doc_entry
        for (doc_entry,) in db.query(Order.sap_doc_entry)
        .filter(Order.sap_doc_entry.in_(doc_entries_seen))
        .all()
    } if doc_entries_seen else set()

    new_orders: list[Order] = []
    latest_date = checkpoint
    for raw in raw_orders:
        order_date = datetime.strptime(raw["DocDate"][:10], "%Y-%m-%d").date()
        latest_date = max(latest_date, order_date)

        if raw["DocEntry"] in existing_doc_entries:
            continue

        customer = _get_or_create_customer(db, raw["CardCode"])
        order = Order(
            customer_id=customer.id,
            sap_doc_entry=raw["DocEntry"],
            sap_doc_num=str(raw.get("DocNum", "")),
            order_date=order_date,
            amount=raw["DocTotal"],
        )
        db.add(order)
        db.flush()
        new_orders.append(order)

    _set_checkpoint(db, latest_date)
    db.commit()
    return new_orders
