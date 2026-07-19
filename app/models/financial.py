import enum
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class FinancialRecordStatus(str, enum.Enum):
    PAGO_EM_DIA = "pago_em_dia"
    PAGO_EM_ATRASO = "pago_em_atraso"
    ABERTO_DENTRO_PRAZO = "aberto_dentro_prazo"
    ABERTO_VENCIDO = "aberto_vencido"


class FinancialRecord(Base):
    """Lançamento de contas a receber sincronizado do SAP B1 (título/fatura)."""

    __tablename__ = "financial_records"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)

    sap_doc_entry: Mapped[int] = mapped_column(index=True)
    sap_doc_num: Mapped[str | None] = mapped_column(String(30), nullable=True)

    issue_date: Mapped[date] = mapped_column(Date)
    due_date: Mapped[date] = mapped_column(Date)
    payment_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    amount: Mapped[float] = mapped_column(Numeric(18, 2))
    amount_paid: Mapped[float] = mapped_column(Numeric(18, 2), default=0)

    status: Mapped[FinancialRecordStatus] = mapped_column(Enum(FinancialRecordStatus))
    days_late: Mapped[int] = mapped_column(default=0)

    synced_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    customer: Mapped["Customer"] = relationship(back_populates="financial_records")


class OrderStatus(str, enum.Enum):
    EM_ANALISE = "em_analise"
    APROVADO = "aprovado"
    APROVADO_COM_RESSALVA = "aprovado_com_ressalva"
    BLOQUEADO = "bloqueado"
    REJEITADO = "rejeitado"


class Order(Base):
    """Novo pedido de venda recebido do SAP B1, disparando a análise de crédito."""

    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)

    sap_doc_entry: Mapped[int] = mapped_column(unique=True, index=True)
    sap_doc_num: Mapped[str | None] = mapped_column(String(30), nullable=True)

    order_date: Mapped[date] = mapped_column(Date)
    amount: Mapped[float] = mapped_column(Numeric(18, 2))

    # Consumo total no momento da análise: faturado em aberto + este pedido
    total_consumption_at_analysis: Mapped[float | None] = mapped_column(
        Numeric(18, 2), nullable=True
    )
    credit_limit_at_analysis: Mapped[float | None] = mapped_column(
        Numeric(18, 2), nullable=True
    )

    status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus), default=OrderStatus.EM_ANALISE
    )
    analyzed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    received_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # Preenchidos quando um usuário decide manualmente um pedido em
    # "aprovado_com_ressalva" ou "bloqueado" (ver POST /orders/{id}/decision)
    reviewed_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    review_notes: Mapped[str | None] = mapped_column(String(500), nullable=True)

    customer: Mapped["Customer"] = relationship(back_populates="orders")
