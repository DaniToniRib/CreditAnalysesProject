"""Cálculo de consumo de crédito: faturado em aberto + pedido novo."""

from app.models.customer import Customer
from app.models.financial import FinancialRecordStatus


def total_open_receivables(customer: Customer) -> float:
    """Soma de títulos ainda não pagos (dentro do prazo + vencidos)."""
    open_statuses = {
        FinancialRecordStatus.ABERTO_DENTRO_PRAZO,
        FinancialRecordStatus.ABERTO_VENCIDO,
    }
    return sum(
        float(r.amount) - float(r.amount_paid)
        for r in customer.financial_records
        if r.status in open_statuses
    )


def total_consumption(customer: Customer, new_order_amount: float) -> float:
    """Consumo total considerado na análise: faturado em aberto + pedido novo."""
    return total_open_receivables(customer) + new_order_amount


def has_overdue_open_balance(customer: Customer) -> bool:
    return any(
        r.status == FinancialRecordStatus.ABERTO_VENCIDO for r in customer.financial_records
    )
