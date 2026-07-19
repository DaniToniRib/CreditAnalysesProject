"""Cliente para o SAP Business One Service Layer (API REST/OData do B1).

Referência: https://help.sap.com/docs/SAP_BUSINESS_ONE_SERVICE_LAYER

TODO ao integrar com o SAP real:
- Confirmar o campo exato de CNPJ/CPF em `BusinessPartners` na localização
  Brasil (assumido `FederalTaxID` abaixo; em instalações mais antigas pode
  ser `LicTradNum` — confirmar com T.I.).
- Confirmar se o Service Layer em uso expõe a data efetiva de pagamento do
  título. A entidade `Invoices` padrão não tem um campo de "data de
  pagamento"; abaixo usamos `UpdateDate` como aproximação quando o
  documento está fechado (`DocumentStatus == bost_Close`), o que é apenas
  uma estimativa — o ideal é cruzar com `IncomingPayments` (coleção
  `PaymentInvoices`) para obter a data real da baixa.
- Confirmar se pedidos de venda usam a entidade `Orders` (padrão do B1) e
  se há necessidade de filtrar por tipo de documento/filial.
"""

from datetime import date

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import get_settings

settings = get_settings()

# Página razoável para não sobrecarregar o Service Layer em consultas amplas
PAGE_SIZE = 100


class SAPServiceLayerClient:
    def __init__(self) -> None:
        self._client = httpx.Client(
            base_url=settings.sap_service_layer_url,
            verify=settings.sap_verify_ssl,
            timeout=30.0,
        )
        self._session_id: str | None = None

    def _login(self) -> None:
        response = self._client.post(
            "/Login",
            json={
                "CompanyDB": settings.sap_company_db,
                "UserName": settings.sap_username,
                "Password": settings.sap_password,
            },
        )
        response.raise_for_status()
        self._session_id = response.json()["SessionId"]

    def _ensure_session(self) -> None:
        if self._session_id is None:
            self._login()

    @retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=1, max=5))
    def _request(self, method: str, path: str, **kwargs) -> httpx.Response:
        self._ensure_session()
        response = self._client.request(method, path, **kwargs)
        if response.status_code == 401:
            # Sessão expirada (padrão: 30 min de inatividade) — refaz login uma vez
            self._login()
            response = self._client.request(method, path, **kwargs)
        response.raise_for_status()
        return response

    def _get_all_pages(self, path: str, params: dict) -> list[dict]:
        """Segue `odata.nextLink` até esgotar os resultados."""
        results: list[dict] = []
        params = {**params, "$top": PAGE_SIZE}
        next_path, next_params = path, params

        while True:
            response = self._request("GET", next_path, params=next_params)
            payload = response.json()
            results.extend(payload.get("value", []))

            next_link = payload.get("odata.nextLink") or payload.get("@odata.nextLink")
            if not next_link:
                break
            # nextLink já vem com a query string completa (inclui $skip) —
            # não reaplicar os params originais na próxima chamada
            next_path, next_params = next_link, {}

        return results

    def get_business_partner(self, card_code: str) -> dict:
        response = self._request("GET", f"/BusinessPartners('{card_code}')")
        return response.json()

    def get_receivables_history(self, card_code: str, since: date) -> list[dict]:
        """Histórico de títulos de contas a receber (pagos e em aberto) desde `since`."""
        params = {
            "$filter": f"CardCode eq '{card_code}' and DocDate ge {since.isoformat()}",
            "$select": (
                "DocEntry,DocNum,DocDate,DocDueDate,DocTotal,PaidToDate,"
                "DocumentStatus,UpdateDate"
            ),
        }
        return self._get_all_pages("/Invoices", params)

    def get_orders_since(self, since: date) -> list[dict]:
        """Pedidos de venda criados a partir de uma data, para detectar novos pedidos."""
        params = {
            "$filter": f"DocDate ge {since.isoformat()}",
            "$select": "DocEntry,DocNum,CardCode,DocDate,DocTotal",
            "$orderby": "DocDate asc",
        }
        return self._get_all_pages("/Orders", params)

    def close(self) -> None:
        self._client.close()
