"""Sincroniza o histórico financeiro do cliente a partir do SAP B1."""

from datetime import date, datetime

from sqlalchemy.orm import Session

from app.connectors.sap_service_layer import SAPServiceLayerClient
from app.models.customer import Customer
from app.models.financial import FinancialRecord, FinancialRecordStatus


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


def sync_customer_financial_history(
    db: Session, customer: Customer, sap_client: SAPServiceLayerClient
) -> list[FinancialRecord]:
    """Busca os títulos do cliente no SAP e atualiza (upsert) `financial_records`."""

    today = date.today()
    raw_records = sap_client.get_open_receivables(customer.sap_card_code)

    existing_by_doc = {
        r.sap_doc_entry: r for r in customer.financial_records
    }

    synced: list[FinancialRecord] = []
    for raw in raw_records:
        due = datetime.strptime(raw["DocDueDate"][:10], "%Y-%m-%d").date()
        payment_date = None  # TODO: SAP não expõe data de pagamento direto em Invoices;
        # normalmente vem de IncomingPayments vinculado via DocEntry — a implementar
        # junto com T.I. ao validar o fluxo de baixa real.

        status, days_late = _classify_status(due, payment_date, today)

        record = existing_by_doc.get(raw["DocEntry"])
        if record is None:
            record = FinancialRecord(
                customer_id=customer.id,
                sap_doc_entry=raw["DocEntry"],
            )
            db.add(record)

        record.sap_doc_num = str(raw.get("DocNum", ""))
        record.issue_date = datetime.strptime(raw["DocDate"][:10], "%Y-%m-%d").date()
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
