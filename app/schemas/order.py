from datetime import date, datetime

from pydantic import BaseModel, Field

from app.models.financial import OrderStatus


class NewOrderIn(BaseModel):
    """Payload para criação manual de um pedido (alternativa ao polling do SAP)."""

    sap_card_code: str = Field(min_length=1, max_length=15)
    sap_doc_entry: int = Field(gt=0)
    sap_doc_num: str | None = Field(default=None, max_length=30)
    order_date: date
    amount: float = Field(gt=0)


class OrderAnalysisOut(BaseModel):
    sap_doc_entry: int
    status: OrderStatus
    total_consumption_at_analysis: float | None
    credit_limit_at_analysis: float | None
    analyzed_at: datetime | None

    model_config = {"from_attributes": True}


class OrderPendingOut(BaseModel):
    """Item da fila de pedidos que precisam de decisão humana."""

    id: int
    sap_card_code: str
    customer_name: str
    sap_doc_num: str | None
    amount: float
    total_consumption_at_analysis: float | None
    credit_limit_at_analysis: float | None
    status: OrderStatus
    analyzed_at: datetime | None


class OrderDecisionIn(BaseModel):
    """Decisão manual sobre um pedido em 'aprovado_com_ressalva' ou 'bloqueado'."""

    approve: bool
    reviewer: str = Field(min_length=1, max_length=100)
    notes: str | None = Field(default=None, max_length=500)
