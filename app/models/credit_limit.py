from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class CreditLimitHistory(Base):
    """Histórico de cálculo/aplicação do limite de crédito derivado do Score."""

    __tablename__ = "credit_limit_history"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)
    score_history_id: Mapped[int | None] = mapped_column(
        ForeignKey("credit_score_history.id"), nullable=True
    )

    calculated_limit: Mapped[float] = mapped_column(Numeric(18, 2))
    rule_version: Mapped[str] = mapped_column(String(50))

    # Preenchido quando um usuário sobrescreve manualmente o limite calculado
    manual_override_limit: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)
    override_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    overridden_by: Mapped[str | None] = mapped_column(String(100), nullable=True)

    computed_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    customer: Mapped["Customer"] = relationship(back_populates="credit_limit_history")
