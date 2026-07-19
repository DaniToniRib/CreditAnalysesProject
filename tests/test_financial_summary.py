from datetime import date, datetime

from app.models.financial import FinancialRecord, FinancialRecordStatus
from app.models.score import CreditScoreHistory
from app.services.financial_summary import summarize_financial_history, summarize_score_trend


def _record(status, amount, days_late=0):
    return FinancialRecord(
        sap_doc_entry=1,
        issue_date=date(2026, 1, 1),
        due_date=date(2026, 1, 10),
        amount=amount,
        amount_paid=amount,
        status=status,
        days_late=days_late,
    )


def test_summarize_financial_history_splits_by_status():
    records = [
        _record(FinancialRecordStatus.PAGO_EM_DIA, 100),
        _record(FinancialRecordStatus.PAGO_EM_ATRASO, 200, days_late=10),
        _record(FinancialRecordStatus.PAGO_EM_ATRASO, 300, days_late=20),
        _record(FinancialRecordStatus.ABERTO_DENTRO_PRAZO, 50),
        _record(FinancialRecordStatus.ABERTO_VENCIDO, 75, days_late=5),
    ]

    summary = summarize_financial_history(records)

    assert summary.paid_on_time_count == 1
    assert summary.paid_on_time_amount == 100
    assert summary.paid_late_count == 2
    assert summary.paid_late_amount == 500
    assert summary.avg_days_late_paid == 15
    assert summary.open_on_time_count == 1
    assert summary.open_overdue_count == 1
    assert summary.avg_days_late_open == 5
    assert summary.total_count == 5
    assert summary.total_amount == 725


def test_summarize_financial_history_empty_list():
    summary = summarize_financial_history([])

    assert summary.total_count == 0
    assert summary.total_amount == 0
    assert summary.avg_days_late_paid is None
    assert summary.avg_days_late_open is None


def _score(computed_at, score):
    return CreditScoreHistory(
        customer_id=1,
        default_probability=0.1,
        score=score,
        model_version="test",
        computed_at=computed_at,
    )


def test_score_trend_detects_improvement():
    trend = summarize_score_trend(
        [_score(datetime(2026, 1, 1), 500), _score(datetime(2026, 6, 1), 700)]
    )

    assert trend.first_score == 500
    assert trend.last_score == 700
    assert trend.delta == 200
    assert trend.direction == "melhora"


def test_score_trend_detects_decline():
    trend = summarize_score_trend(
        [_score(datetime(2026, 1, 1), 700), _score(datetime(2026, 6, 1), 500)]
    )

    assert trend.delta == -200
    assert trend.direction == "piora"


def test_score_trend_stable():
    trend = summarize_score_trend(
        [_score(datetime(2026, 1, 1), 600), _score(datetime(2026, 6, 1), 600)]
    )

    assert trend.delta == 0
    assert trend.direction == "estavel"


def test_score_trend_insufficient_history():
    trend = summarize_score_trend([_score(datetime(2026, 1, 1), 600)])

    assert trend.delta is None
    assert trend.direction == "sem_historico_suficiente"


def test_score_trend_sorts_out_of_order_input():
    trend = summarize_score_trend(
        [_score(datetime(2026, 6, 1), 700), _score(datetime(2026, 1, 1), 500)]
    )

    assert trend.first_score == 500
    assert trend.last_score == 700
