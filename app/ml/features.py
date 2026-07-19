"""Feature engineering: histórico de relacionamento (SAP) + dados Serasa.

O conjunto de features abaixo é um ponto de partida — ao treinar o modelo
com dados reais (ver `train.py`), revisar quais variáveis têm poder
discriminante (ex.: via análise de coeficientes/WOE) e ajustar aqui.
"""

from app.models.customer import Customer
from app.models.financial import FinancialRecordStatus
from app.models.serasa import SerasaQuery

FEATURE_NAMES = [
    "pct_paid_on_time",
    "pct_paid_late",
    "avg_days_late",
    "has_overdue_open_balance",
    "relationship_months",
    "serasa_score",
    "serasa_pefin_count",
    "serasa_refin_count",
    "serasa_protests_count",
    "serasa_lawsuits_count",
    "serasa_checks_returned_count",
]


def build_features(customer: Customer, serasa_query: SerasaQuery | None) -> dict[str, float]:
    records = customer.financial_records
    paid_records = [
        r
        for r in records
        if r.status in (FinancialRecordStatus.PAGO_EM_DIA, FinancialRecordStatus.PAGO_EM_ATRASO)
    ]
    total_paid = len(paid_records) or 1  # evita divisão por zero

    paid_on_time = sum(
        1 for r in paid_records if r.status == FinancialRecordStatus.PAGO_EM_DIA
    )
    paid_late = sum(
        1 for r in paid_records if r.status == FinancialRecordStatus.PAGO_EM_ATRASO
    )
    avg_days_late = (
        sum(r.days_late for r in paid_records if r.status == FinancialRecordStatus.PAGO_EM_ATRASO)
        / max(paid_late, 1)
    )
    has_overdue = any(
        r.status == FinancialRecordStatus.ABERTO_VENCIDO for r in records
    )
    relationship_months = _relationship_months(customer)

    return {
        "pct_paid_on_time": paid_on_time / total_paid,
        "pct_paid_late": paid_late / total_paid,
        "avg_days_late": avg_days_late,
        "has_overdue_open_balance": float(has_overdue),
        "relationship_months": relationship_months,
        "serasa_score": float(serasa_query.score) if serasa_query and serasa_query.score else 0.0,
        "serasa_pefin_count": float(serasa_query.pefin_count) if serasa_query else 0.0,
        "serasa_refin_count": float(serasa_query.refin_count) if serasa_query else 0.0,
        "serasa_protests_count": float(serasa_query.protests_count) if serasa_query else 0.0,
        "serasa_lawsuits_count": float(serasa_query.lawsuits_count) if serasa_query else 0.0,
        "serasa_checks_returned_count": (
            float(serasa_query.checks_returned_count) if serasa_query else 0.0
        ),
    }


def _relationship_months(customer: Customer) -> float:
    if not customer.financial_records:
        return 0.0
    earliest = min(r.issue_date for r in customer.financial_records)
    from datetime import date

    return (date.today() - earliest).days / 30.0
