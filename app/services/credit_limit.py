"""Regra de cálculo do limite de crédito a partir do Score interno.

Faixas e multiplicadores abaixo são um ponto de partida — validar com
financeiro/diretoria os valores reais antes de usar em produção
(ver pendência no README).
"""

from app.models.customer import Customer
from app.services.consumption import total_open_receivables

RULE_VERSION = "v0-skeleton"

# (score_minimo, multiplicador sobre o ticket médio mensal faturado)
SCORE_BANDS: list[tuple[int, float]] = [
    (900, 3.0),
    (800, 2.0),
    (700, 1.5),
    (600, 1.0),
    (500, 0.5),
    (0, 0.0),  # score abaixo de 500: sem limite automático, requer análise manual
]

# Score mínimo abaixo do qual nenhum limite automático é concedido,
# independente de faturamento histórico
MIN_SCORE_FOR_AUTO_LIMIT = 500


def _average_monthly_billing(customer: Customer) -> float:
    if not customer.financial_records:
        return 0.0
    total = sum(float(r.amount) for r in customer.financial_records)
    months = max(len({(r.issue_date.year, r.issue_date.month) for r in customer.financial_records}), 1)
    return total / months


def _multiplier_for_score(score: int) -> float:
    for threshold, multiplier in SCORE_BANDS:
        if score >= threshold:
            return multiplier
    return 0.0


def calculate_credit_limit(customer: Customer, score: int) -> float:
    if score < MIN_SCORE_FOR_AUTO_LIMIT:
        return 0.0

    avg_billing = _average_monthly_billing(customer)
    multiplier = _multiplier_for_score(score)
    limit = avg_billing * multiplier

    # Não faz sentido conceder limite menor que o saldo já em aberto do cliente
    limit = max(limit, total_open_receivables(customer))
    return round(limit, 2)
