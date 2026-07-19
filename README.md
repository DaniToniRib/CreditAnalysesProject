# Análise de Crédito de Clientes

Sistema de análise de crédito integrado ao SAP Business One e à Serasa Experian.

## Objetivo

- Ler o histórico de contas a receber do cliente no SAP B1 (pagas, em atraso, em aberto dentro do prazo, vencidas).
- Ao entrar um novo pedido, calcular o consumo total (faturado + pedidos em aberto) frente ao limite de crédito.
- Consultar a Serasa (Score, PEFIN, REFIN, protestos, ações judiciais, cheques) a cada novo pedido, respeitando um cache/TTL para não reconsultar desnecessariamente.
- Exibir um painel por cliente com o histórico de consultas Serasa e os dados da última consulta.
- Calcular um Score interno via regressão logística, combinando histórico de relacionamento (SAP) + dados Serasa.
- Aplicar uma regra de cálculo de limite de crédito a partir do Score, com fila de decisão manual para os casos que estouram o limite.

## Arquitetura

```
                    ┌── poll periódico (5 min) ──> SAP B1 Service Layer (pedidos novos)
Celery beat/worker ─┤
                    └── reavaliação mensal ──────> SAP B1 + Serasa (toda a carteira)

SAP B1 (Service Layer) ──┐
                          ├──> API FastAPI ──> SQL Server (schema próprio)
Serasa Experian API ──────┘         │
                                     ├──> API JSON (X-API-Key) — integrações
                                     └──> Painel HTML /dashboard (HTMX) — uso interno, rede restrita
```

- **Integração SAP B1**: via **Service Layer** (API REST oficial do B1), não acesso direto ao banco — ver [`app/connectors/sap_service_layer.py`](app/connectors/sap_service_layer.py). Detecção de pedido novo é por **polling** (a cada 5 min, `app/services/order_ingestion.py`), já que o Service Layer não garante webhook disponível em toda instalação. `POST /orders` continua existindo como via manual/alternativa.
- **Integração Serasa**: Serasa Experian API (Concentre/CredCheck) — ver [`app/connectors/serasa_client.py`](app/connectors/serasa_client.py).
- **Banco de dados**: SQL Server, para manter uma única stack de banco (o servidor roda em Ubuntu, mas o SGBD é Microsoft).
- **Scoring**: `scikit-learn` (regressão logística), treinado a partir do histórico de pagamento + dados Serasa. Reavaliação em dois gatilhos: (1) novo pedido, (2) job periódico (mensal) para toda a base.
- **Decisão de crédito**: pedido dentro do limite é aprovado automaticamente; acima do limite sem restrição grave na Serasa vai para **aprovado com ressalva**; com PEFIN/protesto/ação judicial vai para **bloqueado**. Ambos os casos entram na fila de revisão humana (`GET /dashboard/orders/queue`).
- **Autenticação**: a API JSON (`/customers`, `/orders`) exige header `X-API-Key`, pensada para integrações (SAP, outros sistemas). O painel HTML (`/dashboard/...`) não exige API key — deve ficar restrito por rede/VPN (ver `docs/recomendacoes-ti.md`).
- **Painel**: server-rendered (Jinja2/HTMX) para simplicidade de deploy — pode ser trocado por um frontend separado (Next.js) depois, sem alterar a API.
- **Relatório em PDF**: `GET /customers/{card_code}/report.pdf` (API) e `GET /dashboard/customers/{card_code}/report.pdf` (painel, botão "Baixar relatório em PDF") geram um PDF com resumo financeiro (total pago em dia, pago em atraso com atraso médio em dias, em aberto no prazo e vencido), evolução do Score no período (gráfico + tabela, com indicação de melhora/piora) e a última consulta Serasa — ver `app/services/pdf_report.py`. Parâmetro `?months=N` controla o período (padrão 12 meses).

## Estrutura do projeto

```
app/
  config.py               Configurações (via .env)
  database.py              Engine/Session SQLAlchemy
  logging_config.py        Configuração de logging (API e workers)
  models/                   Tabelas: cliente, histórico financeiro, pedidos, consultas Serasa, score, limite, checkpoint de sync
  schemas/                  Schemas Pydantic (I/O da API)
  connectors/                Clientes SAP Service Layer e Serasa
  services/                  Regras de negócio (sync cadastro/histórico, ingestão de pedidos, consumo, score, limite, decisão, painel, relatório PDF)
  api/routes/                 customers.py e orders.py (API JSON, API key) + dashboard.py (painel HTML, rede restrita)
  tasks/                      Celery (polling de pedidos, análise, reavaliação periódica)
  ml/                         Feature engineering e treino do modelo
migrations/                  Alembic (0001_initial cobre o schema completo)
docs/                        Documentação para T.I. (deploy em Ubuntu)
scripts/                      Scripts de instalação/deploy
```

## Fluxo de um pedido novo

1. `poll_new_orders_task` (a cada 5 min) busca pedidos novos no SAP e cria `Order` local com status `em_analise`.
2. `analyze_order_task` sincroniza cadastro + histórico financeiro do cliente, consulta a Serasa (respeitando o TTL), calcula Score e limite, e decide: `aprovado`, `aprovado_com_ressalva` ou `bloqueado`.
3. Pedidos que não foram aprovados automaticamente aparecem em `GET /dashboard/orders/queue`, onde um humano aprova/rejeita (`POST /dashboard/orders/{id}/decision`), registrando quem decidiu e por quê.
4. O painel do cliente (`GET /dashboard/customers/{card_code}`) mostra Score atual, limite atual, última consulta Serasa e os históricos completos.

## Segurança

Auditoria de segurança feita em 2026-07-19 (ver histórico de commits). Resumo do que foi encontrado e corrigido:

- **Injeção OData no conector SAP** (crítico): `card_code` era interpolado sem escape nos filtros OData enviados ao Service Layer, permitindo que um valor malicioso alterasse a consulta (ex.: `X' or CardCode eq 'Y`). Corrigido em `app/connectors/sap_service_layer.py` (escape de aspas simples + URL-encoding).
- **`.env` podia vazar para dentro da imagem Docker**: não havia `.dockerignore`. Adicionado, excluindo `.env`, `.git`, artefatos de teste/ML etc. do build context.
- **URL de conexão do SQL Server montada por f-string**: uma senha com `@`, `:`, `/` ou `?` quebrava (ou distorcia) a connection string. Trocado para `sqlalchemy.engine.URL.create(...)`, que escapa corretamente.
- **Celery sem serializer explícito**: se o broker Redis fosse comprometido, um serializer pickle permitiria execução remota de código ao desserializar uma task maliciosa. Fixado explicitamente em JSON.
- **Sem rate limiting nem headers de segurança**: adicionado `app/api/middleware.py` — limite de requisições por IP (`RATE_LIMIT_PER_MINUTE`, padrão 120/min, contador no Redis) e headers `X-Content-Type-Options`, `X-Frame-Options`, `Content-Security-Policy`, `Referrer-Policy` em toda resposta.
- **Dependências com CVEs conhecidas**: `jinja2` (CVE-2025-27516) e `python-multipart` (CVE-2026-53539, CVE-2026-40347, CVE-2026-24486) foram atualizadas para versões corrigidas. `.github/dependabot.yml` adicionado para monitoramento contínuo (falta habilitar "Dependabot alerts" nas configurações do repositório no GitHub — não é algo configurável por arquivo).
- **Validação de entrada**: parâmetro `?months=` nos endpoints de relatório PDF agora tem limites (1–120); payloads de pedido/decisão/override de limite ganharam validação de tamanho/sinal nos campos.
- **`TrustServerCertificate` fixo no código**: virou configurável (`DB_TRUST_SERVER_CERTIFICATE`, padrão `true` para instalações on-prem com certificado autoassinado — trocar para `false` quando houver certificado válido).

Aceito conscientemente (decisão já discutida com o usuário): o painel HTML (`/dashboard/...`) não tem autenticação própria — depende de restrição de rede/VPN, documentado em `docs/recomendacoes-ti.md`. A única saída de rede do sistema é a consulta à Serasa (inerente à funcionalidade); o painel carrega `htmx.js` via CDN pública por decisão explícita do usuário.

## Setup local

```bash
cp .env.example .env   # preencher credenciais SAP, Serasa, SQL Server e API_KEY
docker compose up --build
docker compose exec api alembic upgrade head
```

API disponível em `http://localhost:8000`. Documentação automática em `/docs`. Painel em `http://localhost:8000/dashboard/orders/queue`.

## Testes

```bash
pip install -r requirements.txt
pytest
```

**Nota:** os testes cobrem lógica pura (classificação de status financeiro, consumo, limite, score heurístico, resumo financeiro/tendência de Score, dedupe de ingestão de pedidos via SQLite em memória, formatação de log JSON, escape de injeção OData, rate limiting) e não dependem de SQL Server real. As 34 asserções passam (`34 passed`), executadas de fato nesta máquina — não é confirmado só por leitura de código. Lacunas conhecidas: (1) `scikit-learn`/`pandas` não instalam nesta instalação específica de Python 3.14 (módulo `ctypes` quebrado), então o caminho de `app/services/scoring.py` que carrega um modelo `.joblib` já treinado não foi exercitado; (2) importar `app.main` fim a fim nesta máquina esbarra em outra consequência do mesmo `ctypes` quebrado (o `click`, dependência do Celery, usa `ctypes` só para suporte a console do Windows) — não afeta o container Docker/Linux de destino, onde esse código sequer é executado. O gerador de PDF (`app/services/pdf_report.py`) foi validado gerando um PDF real com dados fictícios via o próprio código do projeto. Rodar a suíte completa no container Docker cobre essas lacunas.

## Status

Esqueleto funcional e integrado ponta a ponta (ingestão → análise → decisão → painel), mas a lógica de negócio ainda usa placeholders onde depende de informação externa não confirmada — ver "Pendências conhecidas".

## Pendências conhecidas

- [ ] Confirmar com T.I. os campos exatos do Service Layer para pagamentos/baixas (`app/connectors/sap_service_layer.py` e `app/services/history_sync.py` usam `UpdateDate` como aproximação da data de pagamento — o ideal é cruzar com `IncomingPayments`).
- [ ] Confirmar o campo de CNPJ/CPF em `BusinessPartners` na localização Brasil (`app/services/customer_sync.py` assume `FederalTaxID`).
- [ ] Obter credenciais e documentação real da Serasa Experian API (Concentre/CredCheck) contratada — nomes de campos no payload em `app/connectors/serasa_client.py` são um mapeamento provisório.
- [ ] Definir regra exata da fórmula de limite de crédito a partir do Score (faixas e multiplicadores em `app/services/credit_limit.py` são placeholders).
- [ ] Levantar dataset histórico de inadimplência para treinar o modelo de regressão logística (`app/ml/train.py`); até lá, o sistema usa uma heurística de fallback.
- [ ] Gerar um `API_KEY` real (`openssl rand -hex 32`) e distribuir apenas para as integrações que devem chamar a API.
