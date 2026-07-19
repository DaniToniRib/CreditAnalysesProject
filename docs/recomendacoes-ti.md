# Recomendações para T.I. — Análise de Crédito de Clientes

## Requisitos de infraestrutura

- **Servidor de aplicação**: Ubuntu Server 22.04+ (ou compatível), com Docker e Docker Compose instalados.
- **Banco de dados**: SQL Server (2019+), pode ser instância dedicada ou a mesma instância do SAP B1 — recomenda-se **schema/database separado** do SBO, apenas com acesso de leitura ao banco do SAP quando necessário.
- **Acesso de rede**: o servidor precisa alcançar:
  - O **SAP Service Layer** do B1 (porta padrão `50000`, HTTPS).
  - A **API da Serasa Experian** (internet, HTTPS de saída).
  - A instância SQL Server (porta `1433`).

## Contas de serviço necessárias

- Usuário do SAP B1 dedicado para o Service Layer, com permissão de leitura em Business Partners, Invoices e Orders (evitar usar usuário administrativo).
- Credenciais da API Serasa Experian (client_id/client_secret do produto Concentre/CredCheck contratado).
- Usuário SQL Server com permissão de `db_owner` apenas no banco próprio da aplicação (`analise_credito`).

## Deploy

```bash
git clone <repo>
cd CreditAnalysesProject
cp .env.example .env   # preencher com as credenciais acima
docker compose up -d --build
docker compose exec api alembic upgrade head
```

Serviços:
- `api`: aplicação FastAPI (porta 8000) — expõe a API JSON (`/customers`, `/orders`, protegida por `X-API-Key`) e o painel HTML (`/dashboard/...`, sem API key)
- `worker`: processa análises de crédito assíncronas (Celery)
- `beat`: agenda o polling de pedidos novos (5 em 5 min) e a reavaliação mensal da carteira
- `redis`: fila de tasks

Painel para uso do financeiro/comercial: `http://<servidor>:8000/dashboard/orders/queue`.

## Backups

- Banco de dados: backup diário do SQL Server (`analise_credito`), retenção mínima de 30 dias — contém histórico de score, limites e consultas Serasa (dado sensível/auditável).
- `.env`: não versionar; manter cópia segura fora do servidor (contém credenciais).

## Segurança

- Restringir acesso à porta 8000 à rede interna ou VPN — o painel `/dashboard/...` **não** exige autenticação própria (pensado para uso interno) e depende inteiramente dessa restrição de rede. Não expor a porta 8000 diretamente à internet.
- A API JSON (`/customers`, `/orders`) exige o header `X-API-Key`. Gerar um valor forte (`openssl rand -hex 32`) para a variável `API_KEY` no `.env` e distribuí-lo apenas às integrações que precisam chamar a API (ex.: outro sistema interno que cria pedidos manualmente).
- Rotacionar credenciais da Serasa, do usuário SAP e o `API_KEY` periodicamente.
- Habilitar TLS na frente da API (reverse proxy — Nginx/Caddy) antes de expor além da rede interna.
- **`DB_TRUST_SERVER_CERTIFICATE`**: vem `true` por padrão (aceita certificado autoassinado do SQL Server, comum em instalações on-prem). Assim que houver um certificado válido configurado no SQL Server, trocar para `false` no `.env` — caso contrário a conexão com o banco fica exposta a ataques man-in-the-middle.
- **Habilitar "Dependabot alerts"** no repositório GitHub (Settings → Security → Code security → Dependabot alerts). Já existe `.github/dependabot.yml` configurado para abrir PRs semanais de atualização de dependências Python/Docker, mas o alerta de vulnerabilidade em si precisa ser ligado manualmente nas configurações do repositório (não é algo que se configura por arquivo).
- **Redis**: não fica exposto fora da rede interna do Docker Compose (nenhuma porta publicada para o host) — não expor a porta 6379 ao publicar o compose em produção, mesmo que pareça conveniente para debug.
- **Rate limiting**: a API limita requisições por IP (`RATE_LIMIT_PER_MINUTE` no `.env`, padrão 120/min) para dificultar força bruta contra a `API_KEY` e abuso do painel. Se algum sistema legítimo fizer picos de requisição maiores que isso, ajustar essa variável.

### Checklist de atualização de dependências (revisão de segurança de 2026-07-19)

As seguintes dependências tinham CVEs conhecidas nas versões originalmente fixadas e foram atualizadas no `requirements.txt`:

| Pacote | Versão antiga | Versão corrigida | CVE(s) |
|---|---|---|---|
| `jinja2` | 3.1.4 | 3.1.6 | CVE-2025-27516 (sandbox breakout) |
| `python-multipart` | 0.0.19 | 0.0.32 | CVE-2026-53539, CVE-2026-40347, CVE-2026-24486 |

Ao atualizar dependências no futuro, rodar `pip list --outdated` e conferir CVEs conhecidas (ex.: `pip-audit`) antes de subir para produção — o Dependabot (uma vez com os alertas habilitados) automatiza parte disso.

## Systemd (alternativa sem Docker)

Caso a T.I. prefira não usar Docker, os mesmos serviços (`api`, `worker`, `beat`) podem rodar como unidades `systemd` chamando `uvicorn`/`celery` diretamente dentro de um virtualenv — seguir o mesmo padrão adotado no projeto `monitor-nfe`.
