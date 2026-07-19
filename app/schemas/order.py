from datetime import date, datetime

from pydantic import BaseModel

from app.models.financial import OrderStatus


class NewOrderIn(BaseModel):
    """Payload recebido quando um novo pedido é criado no SAP B1."""

    sap_card_code: str
    sap_doc_entry: int
    sap_doc_num: str | None = None
    order_date: date
    amount: float


class OrderAnalysisOut(BaseModel):
    sap_doc_entry: int
    status: OrderStatus
    total_consumption_at_analysis: float | None
    credit_limit_at_analysis: float | None
    analyzed_at: datetime | None

    model_config = {"from_attributes": True}
