from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, Numeric, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class SerasaQuery(Base):
    """Consulta realizada na Serasa Experian API para um cliente/pedido."""

    __tablename__ = "serasa_queries"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)
    order_id: Mapped[int | None] = mapped_column(ForeignKey("orders.id"), nullable=True)

    score: Mapped[int | None] = mapped_column(Integer, nullable=True)

    pefin_count: Mapped[int] = mapped_column(default=0)
    pefin_total_amount: Mapped[float] = mapped_column(Numeric(18, 2), default=0)

    refin_count: Mapped[int] = mapped_column(default=0)
    refin_total_amount: Mapped[float] = mapped_column(Numeric(18, 2), default=0)

    protests_count: Mapped[int] = mapped_column(default=0)
    protests_total_amount: Mapped[float] = mapped_column(Numeric(18, 2), default=0)

    lawsuits_count: Mapped[int] = mapped_column(default=0)

    checks_returned_count: Mapped[int] = mapped_column(default=0)

    # Payload bruto retornado pela API, para auditoria/reprocessamento
    raw_response: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    queried_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    customer: Mapped["Customer"] = relationship(back_populates="serasa_queries")
