"""Sincroniza o histórico financeiro do cliente a partir do SAP B1."""

from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from app.connectors.sap_service_layer import SAPServiceLayerClient
from app.models.customer import Customer
from app.models.financial import FinancialRecord, FinancialRecordStatus

# Quantos meses de histórico buscar no SAP a cada sync (equilíbrio entre
# ter dados suficientes para o score e não sobrecarregar o Service Layer)
HISTORY_LOOKBACK_MONTHS = 24

# Valor observado no Service Layer para documentos encerrados (baixados);
# TODO: confirmar contra o SAP real — pode variar conforme a versão.
SAP_DOCUMENT_STATUS_CLOSED = "bost_Close"


def _parse_sap_date(value: str) -> date:
    return datetime.strptime(value[:10], "%Y-%m-%d").date()


def _classify_status(
    due_date: date, payment_date: date | None, today: date
) -> tuple[FinancialRecordStatus, int]:
    if payment_date is not None:
        days_late = (payment_date - due_date).days
        if days_late > 0:
            return FinancialRecordStatus.PAGO_EM_ATRASO, days_late
        return FinancialRecordStatus.PAGO_EM_DIA, 0

    days_late = (today - due_date).days
    if days_late > 0:
        return FinancialRecordStatus.ABERTO_VENCIDO, days_late
    return FinancialRecordStatus.ABERTO_DENTRO_PRAZO, 0


def _estimate_payment_date(raw: dict) -> date | None:
    """Aproxima a data de pagamento pela última atualização do documento
    fechado. É uma estimativa — ver TODO em `sap_service_layer.py` sobre
    cruzar com `IncomingPayments` para a data real da baixa."""
    if raw.get("DocumentStatus") != SAP_DOCUMENT_STATUS_CLOSED:
        return None
    if raw.get("UpdateDate"):
        return _parse_sap_date(raw["UpdateDate"])
    return _parse_sap_date(raw["DocDueDate"])


def sync_customer_financial_history(
    db: Session, customer: Customer, sap_client: SAPServiceLayerClient
) -> list[FinancialRecord]:
    """Busca os títulos do cliente no SAP (pagos e em aberto) e atualiza
    (upsert) `financial_records`."""

    today = date.today()
    since = today - timedelta(days=HISTORY_LOOKBACK_MONTHS * 30)
    raw_records = sap_client.get_receivables_history(customer.sap_card_code, since)

    existing_by_doc = {r.sap_doc_entry: r for r in customer.financial_records}

    synced: list[FinancialRecord] = []
    for raw in raw_records:
        due = _parse_sap_date(raw["DocDueDate"])
        payment_date = _estimate_payment_date(raw)

        status, days_late = _classify_status(due, payment_date, today)

        record = existing_by_doc.get(raw["DocEntry"])
        if record is None:
            record = FinancialRecord(
                customer_id=customer.id,
                sap_doc_entry=raw["DocEntry"],
            )
            db.add(record)

        record.sap_doc_num = str(raw.get("DocNum", ""))
        record.issue_date = _parse_sap_date(raw["DocDate"])
        record.due_date = due
        record.payment_date = payment_date
        record.amount = raw["DocTotal"]
        record.amount_paid = raw.get("PaidToDate", 0)
        record.status = status
        record.days_late = days_late

        synced.append(record)

    customer.last_sap_sync_at = datetime.utcnow()
    db.commit()
    return synced
