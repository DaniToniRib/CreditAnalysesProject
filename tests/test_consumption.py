from datetime import date, timedelta

from app.models.customer import Customer
from app.models.financial import FinancialRecord, FinancialRecordStatus
from app.services.consumption import (
    has_overdue_open_balance,
    total_consumption,
    total_open_receivables,
)


def _record(status, amount, amount_paid=0):
    return FinancialRecord(
        sap_doc_entry=1,
        issue_date=date.today() - timedelta(days=60),
        due_date=date.today() - timedelta(days=30),
        amount=amount,
        amount_paid=amount_paid,
        status=status,
        days_late=0,
    )


def test_total_open_receivables_sums_only_open_statuses():
    customer = Customer(sap_card_code="C001", name="Cliente Teste")
    customer.financial_records = [
        _record(FinancialRecordStatus.ABERTO_DENTRO_PRAZO, 100),
        _record(FinancialRecordStatus.ABERTO_VENCIDO, 50, amount_paid=20),
        _record(FinancialRecordStatus.PAGO_EM_DIA, 999),
    ]
    assert total_open_receivables(customer) == 100 + (50 - 20)


def test_total_consumption_adds_new_order_to_open_balance():
    customer = Customer(sap_card_code="C001", name="Cliente Teste")
    customer.financial_records = [_record(FinancialRecordStatus.ABERTO_DENTRO_PRAZO, 100)]
    assert total_consumption(customer, 50) == 150


def test_has_overdue_open_balance_true_when_any_record_overdue():
    customer = Customer(sap_card_code="C001", name="Cliente Teste")
    customer.financial_records = [_record(FinancialRecordStatus.ABERTO_VENCIDO, 10)]
    assert has_overdue_open_balance(customer) is True


def test_has_overdue_open_balance_false_when_none_overdue():
    customer = Customer(sap_card_code="C001", name="Cliente Teste")
    customer.financial_records = [_record(FinancialRecordStatus.ABERTO_DENTRO_PRAZO, 10)]
    assert has_overdue_open_balance(customer) is False
