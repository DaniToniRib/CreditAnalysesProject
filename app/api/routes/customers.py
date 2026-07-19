from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates

from app.api.deps import get_customer_or_404
from app.models.customer import Customer
from app.schemas.customer import CustomerPanelOut

router = APIRouter(prefix="/customers", tags=["customers"])
templates = Jinja2Templates(directory=Path(__file__).resolve().parents[2] / "templates")


def _build_panel(customer: Customer) -> CustomerPanelOut:
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


@router.get("/{card_code}/panel", response_model=CustomerPanelOut)
def get_customer_panel_json(customer: Customer = Depends(get_customer_or_404)) -> CustomerPanelOut:
    return _build_panel(customer)


@router.get("/{card_code}")
def get_customer_panel_html(
    request: Request, customer: Customer = Depends(get_customer_or_404)
):
    panel = _build_panel(customer)
    return templates.TemplateResponse(
        "customer_panel.html", {"request": request, "panel": panel}
    )
