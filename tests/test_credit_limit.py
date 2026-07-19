from datetime import date

from app.models.customer import Customer
from app.models.financial import FinancialRecord, FinancialRecordStatus
from app.services.credit_limit import MIN_SCORE_FOR_AUTO_LIMIT, calculate_credit_limit


def _paid_record(month: int, amount: float) -> FinancialRecord:
    return FinancialRecord(
        sap_doc_entry=month,
        issue_date=date(2026, month, 1),
        due_date=date(2026, month, 10),
        payment_date=date(2026, month, 5),
        amount=amount,
        amount_paid=amount,
        status=FinancialRecordStatus.PAGO_EM_DIA,
        days_late=0,
    )


def test_score_below_minimum_returns_zero_limit():
    customer = Customer(sap_card_code="C001", name="Cliente Teste")
    assert calculate_credit_limit(customer, MIN_SCORE_FOR_AUTO_LIMIT - 1) == 0.0


def test_limit_scales_up_with_higher_score():
    customer = Customer(sap_card_code="C001", name="Cliente Teste")
    customer.financial_records = [_paid_record(m, 1000) for m in (1, 2, 3)]

    low_score_limit = calculate_credit_limit(customer, 600)
    high_score_limit = calculate_credit_limit(customer, 900)

    assert high_score_limit > low_score_limit


def test_limit_never_below_open_balance():
    customer = Customer(sap_card_code="C001", name="Cliente Teste")
    customer.financial_records = [
        _paid_record(1, 100),
        FinancialRecord(
            sap_doc_entry=2,
            issue_date=date(2026, 2, 1),
            due_date=date(2026, 2, 10),
            amount=5000,
            amount_paid=0,
            status=FinancialRecordStatus.ABERTO_DENTRO_PRAZO,
            days_late=0,
        ),
    ]
    limit = calculate_credit_limit(customer, 700)
    assert limit >= 5000
