from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_customer_or_404, get_db, verify_api_key
from app.models.credit_limit import CreditLimitHistory
from app.models.customer import Customer
from app.schemas.customer import (
    CreditLimitOverrideIn,
    CustomerListItemOut,
    CustomerPanelOut,
)
from app.services.credit_limit import RULE_VERSION
from app.services.panel import build_customer_panel

router = APIRouter(prefix="/customers", tags=["customers"], dependencies=[Depends(verify_api_key)])


@router.get("", response_model=list[CustomerListItemOut])
def list_customers(db: Session = Depends(get_db)) -> list[CustomerListItemOut]:
    customers = db.query(Customer).order_by(Customer.name.asc()).all()

    result = []
    for customer in customers:
        latest_score = max(customer.score_history, key=lambda s: s.computed_at, default=None)
        latest_limit = max(
            customer.credit_limit_history, key=lambda c: c.computed_at, default=None
        )
        result.append(
            CustomerListItemOut(
                sap_card_code=customer.sap_card_code,
                name=customer.name,
                current_score=latest_score.score if latest_score else None,
                current_credit_limit=(
                    float(latest_limit.calculated_limit) if latest_limit else None
                ),
            )
        )
    return result


@router.get("/{card_code}/panel", response_model=CustomerPanelOut)
def get_customer_panel_json(customer: Customer = Depends(get_customer_or_404)) -> CustomerPanelOut:
    return build_customer_panel(customer)


@router.post("/{card_code}/credit-limit/override", response_model=CustomerPanelOut)
def override_credit_limit(
    payload: CreditLimitOverrideIn,
    db: Session = Depends(get_db),
    customer: Customer = Depends(get_customer_or_404),
) -> CustomerPanelOut:
    """Sobrescreve manualmente o limite de crédito (ex.: decisão da diretoria).

    Cria uma nova entrada no histórico em vez de editar a última, preservando
    a trilha de auditoria de quem alterou o quê e por quê.
    """
    limit_record = CreditLimitHistory(
        customer_id=customer.id,
        calculated_limit=payload.limit,
        manual_override_limit=payload.limit,
        rule_version=RULE_VERSION,
        override_reason=payload.reason,
        overridden_by=payload.overridden_by,
    )
    db.add(limit_record)
    db.commit()
    db.refresh(customer)

    return build_customer_panel(customer)
