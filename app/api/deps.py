import hmac

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models.customer import Customer

__all__ = ["get_db"]

settings = get_settings()


def verify_api_key(x_api_key: str = Header(default="")) -> None:
    if not hmac.compare_digest(x_api_key, settings.api_key):
        raise HTTPException(status_code=401, detail="API key inválida ou ausente")


def get_customer_or_404(card_code: str, db: Session = Depends(get_db)) -> Customer:
    customer = (
        db.query(Customer).filter(Customer.sap_card_code == card_code).one_or_none()
    )
    if customer is None:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    return customer
