"""Painel HTML interno (não usa API key — proteger via rede/VPN, ver docs/recomendacoes-ti.md).

Serve o mesmo dado que a API JSON protegida (`customers.py`, `orders.py`),
mas consulta o banco diretamente para uso em navegador com HTMX, sem exigir
que o operador humano carregue uma API key. Rotas isoladas sob `/dashboard`
para não colidir com a API JSON (ex.: ambas têm um `POST .../decision`,
mas com content-type e autenticação diferentes).
"""

from pathlib import Path

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.api.deps import get_customer_or_404, get_db
from app.models.customer import Customer
from app.models.financial import Order
from app.services.order_review import OrderNotReviewableError, apply_manual_decision
from app.services.panel import build_customer_panel
from app.services.pdf_report import DEFAULT_PERIOD_MONTHS, generate_customer_report_pdf

router = APIRouter(prefix="/dashboard", tags=["dashboard"])
templates = Jinja2Templates(directory=Path(__file__).resolve().parents[2] / "templates")

PENDING_STATUSES = ("em_analise", "aprovado_com_ressalva", "bloqueado")


def _pending_orders(db: Session) -> list[Order]:
    return (
        db.query(Order)
        .filter(Order.status.in_(PENDING_STATUSES))
        .order_by(Order.received_at.asc())
        .all()
    )


@router.get("/customers/{card_code}")
def get_customer_panel_html(request: Request, customer: Customer = Depends(get_customer_or_404)):
    panel = build_customer_panel(customer)
    return templates.TemplateResponse(
        "customer_panel.html", {"request": request, "panel": panel}
    )


@router.get("/customers/{card_code}/report.pdf")
def get_customer_report_pdf_html(
    customer: Customer = Depends(get_customer_or_404),
    months: int = Query(default=DEFAULT_PERIOD_MONTHS, ge=1, le=120),
) -> Response:
    pdf_bytes = generate_customer_report_pdf(customer, months=months)
    filename = f"relatorio-credito-{customer.sap_card_code}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/orders/queue")
def get_orders_queue_html(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse(
        "orders_queue.html", {"request": request, "orders": _pending_orders(db)}
    )


@router.post("/orders/{order_id}/decision")
def decide_order_html(
    order_id: int,
    request: Request,
    approve: bool = Form(...),
    reviewer: str = Form(...),
    notes: str | None = Form(None),
    db: Session = Depends(get_db),
):
    order = db.get(Order, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")

    try:
        apply_manual_decision(db, order, approve, reviewer, notes)
    except OrderNotReviewableError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    return templates.TemplateResponse(
        "_orders_queue_table.html", {"request": request, "orders": _pending_orders(db)}
    )
