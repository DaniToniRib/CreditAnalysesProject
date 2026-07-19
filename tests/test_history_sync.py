from datetime import date

from app.models.financial import FinancialRecordStatus
from app.services.history_sync import (
    SAP_DOCUMENT_STATUS_CLOSED,
    _classify_status,
    _estimate_payment_date,
)


def test_classify_status_paid_on_time():
    status, days_late = _classify_status(date(2026, 1, 10), date(2026, 1, 5), date(2026, 2, 1))
    assert status == FinancialRecordStatus.PAGO_EM_DIA
    assert days_late == 0


def test_classify_status_paid_late():
    status, days_late = _classify_status(date(2026, 1, 10), date(2026, 1, 20), date(2026, 2, 1))
    assert status == FinancialRecordStatus.PAGO_EM_ATRASO
    assert days_late == 10


def test_classify_status_open_within_term():
    status, days_late = _classify_status(date(2026, 3, 1), None, date(2026, 2, 1))
    assert status == FinancialRecordStatus.ABERTO_DENTRO_PRAZO
    assert days_late == 0


def test_classify_status_open_overdue():
    status, days_late = _classify_status(date(2026, 1, 1), None, date(2026, 2, 1))
    assert status == FinancialRecordStatus.ABERTO_VENCIDO
    assert days_late == 31


def test_estimate_payment_date_open_document_returns_none():
    raw = {"DocumentStatus": "bost_Open", "DocDueDate": "2026-01-10", "UpdateDate": "2026-01-05"}
    assert _estimate_payment_date(raw) is None


def test_estimate_payment_date_closed_document_uses_update_date():
    raw = {
        "DocumentStatus": SAP_DOCUMENT_STATUS_CLOSED,
        "DocDueDate": "2026-01-10",
        "UpdateDate": "2026-01-12",
    }
    assert _estimate_payment_date(raw) == date(2026, 1, 12)


def test_estimate_payment_date_closed_document_falls_back_to_due_date():
    raw = {"DocumentStatus": SAP_DOCUMENT_STATUS_CLOSED, "DocDueDate": "2026-01-10"}
    assert _estimate_payment_date(raw) == date(2026, 1, 10)
