from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.customer import Customer

__all__ = ["get_db"]


def get_customer_or_404(card_code: str, db: Session = Depends(get_db)) -> Customer:
    customer = (
        db.query(Customer).filter(Customer.sap_card_code == card_code).one_or_none()
    )
    if customer is None:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    return customer
