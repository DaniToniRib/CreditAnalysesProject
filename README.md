# Análise de Crédito de Clientes

Sistema de análise de crédito integrado ao SAP Business One e à Serasa Experian.

## Objetivo

- Ler o histórico de contas a receber do cliente no SAP B1 (pagas, em atraso, em aberto dentro do prazo, vencidas).
- Ao entrar um novo pedido, calcular o consumo total (faturado + pedidos em aberto) frente ao limite de crédito.
- Consultar a Serasa (Score, PEFIN, REFIN, protestos, ações judiciais, cheques) a cada novo pedido, respeitando um cache/TTL para não reconsultar desnecessariamente.
- Exibir um painel por cliente com o histórico de consultas Serasa e os dados da última consulta.
- Calcular um Score interno via regressão logística, combinando histórico de relacionamento (SAP) + dados Serasa.
- Aplicar uma regra de cálculo de limite de crédito a partir do Score.

## Arquitetura

```
SAP B1 (Service Layer) ──┐
                          ├──> API (FastAPI) ──> SQL Server (schema próprio)
Serasa Experian API ──────┘         │
                                     ├──> Celery worker (consultas Serasa, sync SAP, scoring)
                                     └──> Painel web (Jinja2 + HTMX)
```

- **Integração SAP B1**: via **Service Layer** (API REST oficial do B1), não acesso direto ao banco — ver [`app/connectors/sap_service_layer.py`](app/connectors/sap_service_layer.py).
- **Integração Serasa**: Serasa Experian API (Concentre/CredCheck) — ver [`app/connectors/serasa_client.py`](app/connectors/serasa_client.py).
- **Banco de dados**: SQL Server, para manter uma única stack de banco (o servidor roda em Ubuntu, mas o SGBD é Microsoft).
- **Scoring**: `scikit-learn` (regressão logística), treinado a partir do histórico de pagamento + dados Serasa. Reavaliação em dois gatilhos: (1) novo pedido, (2) job periódico (mensal) para toda a base.
- **Painel**: server-rendered (Jinja2/HTMX) para simplicidade de deploy — pode ser trocado por um frontend separado (Next.js) depois, sem alterar a API.

## Estrutura do projeto

```
app/
  config.py            Configurações (via .env)
  database.py           Engine/Session SQLAlchemy
  models/                Tabelas: cliente, histórico financeiro, pedidos, consultas Serasa, score, limite
  schemas/               Schemas Pydantic (I/O da API)
  connectors/             Clientes SAP Service Layer e Serasa
  services/               Regras de negócio (sync, consumo, score, limite)
  api/routes/             Endpoints FastAPI + painel
  tasks/                  Celery (jobs assíncronos e periódicos)
  ml/                     Feature engineering e treino do modelo
migrations/               Alembic
docs/                     Documentação para T.I. (deploy em Ubuntu)
scripts/                  Scripts de instalação/deploy
```

## Setup local

```bash
cp .env.example .env   # preencher credenciais SAP, Serasa e SQL Server
docker compose up --build
```

API disponível em `http://localhost:8000`. Documentação automática em `/docs`.

## Status

Esqueleto inicial do projeto — módulos criados com interfaces definidas; lógica de negócio e credenciais reais de integração (SAP Service Layer, Serasa) a preencher nas próximas fases.

## Pendências conhecidas

- [ ] Confirmar com T.I. os endpoints/entidades do Service Layer usados para contas a receber e pedidos (provavelmente `InvoiceReceivable`/`Invoices` e `Orders`, a validar o schema real do SAP B1 em uso).
- [ ] Obter credenciais e documentação da Serasa Experian API (Concentre/CredCheck) contratada.
- [ ] Definir regra exata da fórmula de limite de crédito a partir do Score (faixas, multiplicadores).
- [ ] Levantar dataset histórico (pagamentos + resultado, ex.: inadimplência) para treinar o modelo de regressão logística.
