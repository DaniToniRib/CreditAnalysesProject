from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.database import Base
from app.models.financial import Order
from app.services.order_ingestion import poll_new_sap_orders


class FakeSAPClient:
    def __init__(self, orders: list[dict]) -> None:
        self._orders = orders

    def get_orders_since(self, since) -> list[dict]:  # noqa: ANN001 - assinatura do connector real
        return self._orders


def _new_session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_poll_creates_orders_and_customers_for_new_docs():
    db = _new_session()
    raw_orders = [
        {"DocEntry": 1, "DocNum": "1001", "CardCode": "C001", "DocDate": "2026-07-01", "DocTotal": 500},
        {"DocEntry": 2, "DocNum": "1002", "CardCode": "C002", "DocDate": "2026-07-02", "DocTotal": 300},
    ]

    new_orders = poll_new_sap_orders(db, FakeSAPClient(raw_orders))

    assert len(new_orders) == 2
    assert db.query(Order).count() == 2


def test_poll_does_not_duplicate_orders_already_seen():
    db = _new_session()
    raw_orders = [
        {"DocEntry": 1, "DocNum": "1001", "CardCode": "C001", "DocDate": "2026-07-01", "DocTotal": 500},
    ]

    first_pass = poll_new_sap_orders(db, FakeSAPClient(raw_orders))
    second_pass = poll_new_sap_orders(db, FakeSAPClient(raw_orders))

    assert len(first_pass) == 1
    assert second_pass == []
    assert db.query(Order).count() == 1


def test_poll_reuses_existing_customer_by_card_code():
    db = _new_session()
    raw_orders = [
        {"DocEntry": 1, "DocNum": "1001", "CardCode": "C001", "DocDate": "2026-07-01", "DocTotal": 500},
        {"DocEntry": 2, "DocNum": "1002", "CardCode": "C001", "DocDate": "2026-07-03", "DocTotal": 700},
    ]

    poll_new_sap_orders(db, FakeSAPClient(raw_orders))

    orders = db.query(Order).all()
    assert orders[0].customer_id == orders[1].customer_id
