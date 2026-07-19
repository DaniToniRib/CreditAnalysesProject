"""Cliente para a Serasa Experian API (produto Concentre/CredCheck).

TODO ao integrar com a Serasa real:
- Confirmar fluxo de autenticação exato do produto contratado (geralmente
  OAuth2 client_credentials, mas o endpoint/escopo varia por produto).
- Confirmar o endpoint de consulta e o formato exato do payload de resposta
  (nomes de campos para Score, PEFIN, REFIN, protestos, ações judiciais e
  cheques podem diferir do mapeamento abaixo — ajustar `parse_response`).
- Definir tratamento de CPF vs CNPJ (pessoa física x jurídica) se aplicável.
"""

from datetime import datetime, timedelta

import httpx

from app.config import get_settings

settings = get_settings()


class SerasaQueryResult:
    def __init__(
        self,
        score: int | None,
        pefin_count: int,
        pefin_total_amount: float,
        refin_count: int,
        refin_total_amount: float,
        protests_count: int,
        protests_total_amount: float,
        lawsuits_count: int,
        checks_returned_count: int,
        raw_response: dict,
    ) -> None:
        self.score = score
        self.pefin_count = pefin_count
        self.pefin_total_amount = pefin_total_amount
        self.refin_count = refin_count
        self.refin_total_amount = refin_total_amount
        self.protests_count = protests_count
        self.protests_total_amount = protests_total_amount
        self.lawsuits_count = lawsuits_count
        self.checks_returned_count = checks_returned_count
        self.raw_response = raw_response


class SerasaClient:
    def __init__(self) -> None:
        self._client = httpx.Client(base_url=settings.serasa_api_url, timeout=30.0)
        self._access_token: str | None = None
        self._token_expires_at: datetime | None = None

    def _authenticate(self) -> None:
        response = self._client.post(
            "/oauth/token",
            data={
                "grant_type": "client_credentials",
                "client_id": settings.serasa_client_id,
                "client_secret": settings.serasa_client_secret,
            },
        )
        response.raise_for_status()
        payload = response.json()
        self._access_token = payload["access_token"]
        self._token_expires_at = datetime.utcnow() + timedelta(
            seconds=payload.get("expires_in", 3600) - 60
        )

    def _ensure_token(self) -> None:
        if not self._access_token or datetime.utcnow() >= (self._token_expires_at or datetime.min):
            self._authenticate()

    def query_document(self, cnpj_cpf: str) -> SerasaQueryResult:
        self._ensure_token()
        response = self._client.get(
            "/v1/concentre/relato",
            params={"documento": cnpj_cpf},
            headers={"Authorization": f"Bearer {self._access_token}"},
        )
        response.raise_for_status()
        return self._parse_response(response.json())

    @staticmethod
    def _parse_response(payload: dict) -> SerasaQueryResult:
        score_block = payload.get("score", {})
        pefin = payload.get("pefin", {})
        refin = payload.get("refin", {})
        protests = payload.get("protestos", {})
        lawsuits = payload.get("acoesJudiciais", {})
        checks = payload.get("chequesDevolvidos", {})

        return SerasaQueryResult(
            score=score_block.get("pontos"),
            pefin_count=pefin.get("quantidade", 0),
            pefin_total_amount=pefin.get("valorTotal", 0.0),
            refin_count=refin.get("quantidade", 0),
            refin_total_amount=refin.get("valorTotal", 0.0),
            protests_count=protests.get("quantidade", 0),
            protests_total_amount=protests.get("valorTotal", 0.0),
            lawsuits_count=lawsuits.get("quantidade", 0),
            checks_returned_count=checks.get("quantidade", 0),
            raw_response=payload,
        )

    def close(self) -> None:
        self._client.close()
