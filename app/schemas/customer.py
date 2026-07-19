from datetime import date, datetime

from pydantic import BaseModel, Field

from app.models.financial import FinancialRecordStatus


class FinancialRecordOut(BaseModel):
    sap_doc_num: str | None
    issue_date: date
    due_date: date
    payment_date: date | None
    amount: float
    amount_paid: float
    status: FinancialRecordStatus
    days_late: int

    model_config = {"from_attributes": True}


class SerasaQueryOut(BaseModel):
    score: int | None
    pefin_count: int
    pefin_total_amount: float
    refin_count: int
    refin_total_amount: float
    protests_count: int
    protests_total_amount: float
    lawsuits_count: int
    checks_returned_count: int
    queried_at: datetime

    model_config = {"from_attributes": True}


class CreditScoreOut(BaseModel):
    score: int
    default_probability: float
    model_version: str
    computed_at: datetime

    model_config = {"from_attributes": True}


class CreditLimitOut(BaseModel):
    calculated_limit: float
    manual_override_limit: float | None
    rule_version: str
    computed_at: datetime

    model_config = {"from_attributes": True}


class CustomerPanelOut(BaseModel):
    """Payload consolidado do painel do cliente."""

    sap_card_code: str
    name: str
    sap_credit_limit: float | None

    current_score: CreditScoreOut | None
    current_credit_limit: CreditLimitOut | None
    latest_serasa_query: SerasaQueryOut | None

    serasa_query_history: list[SerasaQueryOut]
    financial_history: list[FinancialRecordOut]

    model_config = {"from_attributes": True}


class CustomerListItemOut(BaseModel):
    sap_card_code: str
    name: str
    current_score: int | None
    current_credit_limit: float | None

    model_config = {"from_attributes": True}


class CreditLimitOverrideIn(BaseModel):
    """Sobrescrita manual do limite de crédito calculado (ex.: decisão da diretoria)."""

    limit: float = Field(ge=0)
    reason: str = Field(min_length=1, max_length=500)
    overridden_by: str = Field(min_length=1, max_length=100)
