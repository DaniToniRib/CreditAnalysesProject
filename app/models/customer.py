from datetime import datetime

from sqlalchemy import DateTime, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Customer(Base):
    """Espelho local do cadastro de cliente do SAP B1 (CardCode/CardName)."""

    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    sap_card_code: Mapped[str] = mapped_column(String(15), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    cnpj_cpf: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Limite de crédito cadastrado hoje no SAP, para comparação com o calculado
    sap_credit_limit: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)

    last_sap_sync_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    financial_records: Mapped[list["FinancialRecord"]] = relationship(
        back_populates="customer", cascade="all, delete-orphan"
    )
    orders: Mapped[list["Order"]] = relationship(
        back_populates="customer", cascade="all, delete-orphan"
    )
    serasa_queries: Mapped[list["SerasaQuery"]] = relationship(
        back_populates="customer", cascade="all, delete-orphan"
    )
    score_history: Mapped[list["CreditScoreHistory"]] = relationship(
        back_populates="customer", cascade="all, delete-orphan"
    )
    credit_limit_history: Mapped[list["CreditLimitHistory"]] = relationship(
        back_populates="customer", cascade="all, delete-orphan"
    )
