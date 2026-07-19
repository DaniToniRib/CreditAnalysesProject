"""Monta o payload consolidado do painel do cliente.

Compartilhado entre a API JSON protegida por API key e o painel HTML interno.
"""

from app.models.customer import Customer
from app.schemas.customer import CustomerPanelOut


def build_customer_panel(customer: Customer) -> CustomerPanelOut:
    score_history = sorted(customer.score_history, key=lambda s: s.computed_at, reverse=True)
    limit_history = sorted(
        customer.credit_limit_history, key=lambda c: c.computed_at, reverse=True
    )
    serasa_history = sorted(customer.serasa_queries, key=lambda q: q.queried_at, reverse=True)

    return CustomerPanelOut(
        sap_card_code=customer.sap_card_code,
        name=customer.name,
        sap_credit_limit=customer.sap_credit_limit,
        current_score=score_history[0] if score_history else None,
        current_credit_limit=limit_history[0] if limit_history else None,
        latest_serasa_query=serasa_history[0] if serasa_history else None,
        serasa_query_history=serasa_history,
        financial_history=sorted(
            customer.financial_records, key=lambda r: r.due_date, reverse=True
        ),
    )
