"""Resumo estatístico do histórico financeiro e da evolução do Score.

Usado tanto pelo relatório em PDF (`app/services/pdf_report.py`) quanto,
potencialmente, por outras visões que precisem dos mesmos agregados.
"""

from dataclasses import dataclass, field
from datetime import datetime

from app.models.financial import FinancialRecord, FinancialRecordStatus
from app.models.score import CreditScoreHistory


@dataclass
class FinancialSummary:
    paid_on_time_count: int = 0
    paid_on_time_amount: float = 0.0

    paid_late_count: int = 0
    paid_late_amount: float = 0.0
    avg_days_late_paid: float | None = None

    open_on_time_count: int = 0
    open_on_time_amount: float = 0.0

    open_overdue_count: int = 0
    open_overdue_amount: float = 0.0
    avg_days_late_open: float | None = None

    @property
    def total_count(self) -> int:
        return (
            self.paid_on_time_count
            + self.paid_late_count
            + self.open_on_time_count
            + self.open_overdue_count
        )

    @property
    def total_amount(self) -> float:
        return (
            self.paid_on_time_amount
            + self.paid_late_amount
            + self.open_on_time_amount
            + self.open_overdue_amount
        )


def summarize_financial_history(records: list[FinancialRecord]) -> FinancialSummary:
    summary = FinancialSummary()

    late_paid_days: list[int] = []
    late_open_days: list[int] = []

    for r in records:
        amount = float(r.amount)
        if r.status == FinancialRecordStatus.PAGO_EM_DIA:
            summary.paid_on_time_count += 1
            summary.paid_on_time_amount += amount
        elif r.status == FinancialRecordStatus.PAGO_EM_ATRASO:
            summary.paid_late_count += 1
            summary.paid_late_amount += amount
            late_paid_days.append(r.days_late)
        elif r.status == FinancialRecordStatus.ABERTO_DENTRO_PRAZO:
            summary.open_on_time_count += 1
            summary.open_on_time_amount += amount
        elif r.status == FinancialRecordStatus.ABERTO_VENCIDO:
            summary.open_overdue_count += 1
            summary.open_overdue_amount += amount
            late_open_days.append(r.days_late)

    if late_paid_days:
        summary.avg_days_late_paid = sum(late_paid_days) / len(late_paid_days)
    if late_open_days:
        summary.avg_days_late_open = sum(late_open_days) / len(late_open_days)

    return summary


@dataclass
class ScoreTrendPoint:
    computed_at: datetime
    score: int


@dataclass
class ScoreTrend:
    points: list[ScoreTrendPoint] = field(default_factory=list)

    @property
    def first_score(self) -> int | None:
        return self.points[0].score if self.points else None

    @property
    def last_score(self) -> int | None:
        return self.points[-1].score if self.points else None

    @property
    def delta(self) -> int | None:
        if len(self.points) < 2:
            return None
        return self.last_score - self.first_score

    @property
    def direction(self) -> str:
        delta = self.delta
        if delta is None:
            return "sem_historico_suficiente"
        if delta > 0:
            return "melhora"
        if delta < 0:
            return "piora"
        return "estavel"


def summarize_score_trend(score_history: list[CreditScoreHistory]) -> ScoreTrend:
    ordered = sorted(score_history, key=lambda s: s.computed_at)
    return ScoreTrend(
        points=[ScoreTrendPoint(computed_at=s.computed_at, score=s.score) for s in ordered]
    )
