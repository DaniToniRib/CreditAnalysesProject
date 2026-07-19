"""Sincroniza dados cadastrais do cliente (nome, CNPJ/CPF, limite SAP)."""

from sqlalchemy.orm import Session

from app.connectors.sap_service_layer import SAPServiceLayerClient
from app.models.customer import Customer

# TODO: confirmar o campo de CNPJ/CPF na localização Brasil do SAP em uso
# (`FederalTaxID` é o nome padrão do Service Layer; instalações mais antigas
# podem expor como `LicTradNum`).
CNPJ_CPF_FIELD = "FederalTaxID"


def sync_customer_master_data(
    db: Session, customer: Customer, sap_client: SAPServiceLayerClient
) -> Customer:
    data = sap_client.get_business_partner(customer.sap_card_code)

    customer.name = data.get("CardName", customer.name)
    customer.cnpj_cpf = data.get(CNPJ_CPF_FIELD, customer.cnpj_cpf)
    customer.sap_credit_limit = data.get("CreditLimit", customer.sap_credit_limit)

    db.commit()
    return customer
