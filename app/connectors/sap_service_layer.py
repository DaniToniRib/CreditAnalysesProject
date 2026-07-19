"""Cliente para o SAP Business One Service Layer (API REST/OData do B1).

Referência: https://help.sap.com/docs/SAP_BUSINESS_ONE_SERVICE_LAYER

TODO ao integrar com o SAP real:
- Confirmar os nomes das entidades OData usadas para títulos em aberto/pagos
  (`Invoices` para NF de venda, mas o saldo em aberto normalmente vem de
  `BusinessPartners('{CardCode}')/ARInvoices` ou de uma consulta a
  `BillOfExchangeTransactions` / `IncomingPayments`, dependendo de como o
  financeiro trata baixas parciais). Validar com T.I. o fluxo real de baixa.
- Confirmar se pedidos de venda usam a entidade `Orders`.
"""

from datetime import date

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import get_settings

settings = get_settings()


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

    def get_business_partner(self, card_code: str) -> dict:
        response = self._request("GET", f"/BusinessPartners('{card_code}')")
        return response.json()

    def get_open_receivables(self, card_code: str) -> list[dict]:
        """Títulos de contas a receber em aberto (pagos parcial/integralmente ou não)."""
        params = {
            "$filter": f"CardCode eq '{card_code}'",
            "$select": "DocEntry,DocNum,DocDate,DocDueDate,DocTotal,PaidToDate,DocumentStatus",
        }
        response = self._request("GET", "/Invoices", params=params)
        return response.json().get("value", [])

    def get_orders_since(self, since: date) -> list[dict]:
        """Pedidos de venda criados a partir de uma data, para detectar novos pedidos."""
        params = {
            "$filter": f"DocDate ge {since.isoformat()}",
            "$select": "DocEntry,DocNum,CardCode,DocDate,DocTotal",
        }
        response = self._request("GET", "/Orders", params=params)
        return response.json().get("value", [])

    def close(self) -> None:
        self._client.close()
