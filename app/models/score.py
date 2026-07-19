from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, JSON, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class CreditScoreHistory(Base):
    """Histórico de cálculo do Score interno (regressão logística)."""

    __tablename__ = "credit_score_history"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)
    serasa_query_id: Mapped[int | None] = mapped_column(
        ForeignKey("serasa_queries.id"), nullable=True
    )
    triggered_by_order_id: Mapped[int | None] = mapped_column(
        ForeignKey("orders.id"), nullable=True
    )

    # Probabilidade de inadimplência (saída do modelo) e Score em escala 0-1000
    default_probability: Mapped[float] = mapped_column(Numeric(6, 5))
    score: Mapped[int] = mapped_column()

    model_version: Mapped[str] = mapped_column(String(50))
    # Features usadas no cálculo, para auditoria/explicabilidade
    features_snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    computed_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    customer: Mapped["Customer"] = relationship(back_populates="score_history")
