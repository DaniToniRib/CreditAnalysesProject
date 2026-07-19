"""schema inicial

Revision ID: 0001_initial
Revises:
Create Date: 2026-07-19

Escrita manualmente (não gerada por `alembic revision --autogenerate`) —
o ambiente de desenvolvimento usado nesta sessão não conseguiu rodar o
autogenerate (ver nota no README/memória do projeto). Reflete fielmente os
modelos em `app/models/` no momento da criação; ao evoluir o schema,
prefira gerar as próximas migrations com autogenerate em um ambiente que
consiga se conectar ao SQL Server.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "customers",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("sap_card_code", sa.String(15), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("cnpj_cpf", sa.String(20), nullable=True),
        sa.Column("sap_credit_limit", sa.Numeric(18, 2), nullable=True),
        sa.Column("last_sap_sync_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_customers_sap_card_code", "customers", ["sap_card_code"], unique=True)

    op.create_table(
        "financial_records",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("customer_id", sa.Integer(), sa.ForeignKey("customers.id"), nullable=False),
        sa.Column("sap_doc_entry", sa.Integer(), nullable=False),
        sa.Column("sap_doc_num", sa.String(30), nullable=True),
        sa.Column("issue_date", sa.Date(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("payment_date", sa.Date(), nullable=True),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("amount_paid", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column(
            "status",
            sa.Enum(
                "pago_em_dia",
                "pago_em_atraso",
                "aberto_dentro_prazo",
                "aberto_vencido",
                name="financial_record_status",
            ),
            nullable=False,
        ),
        sa.Column("days_late", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("synced_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index(
        "ix_financial_records_customer_id", "financial_records", ["customer_id"]
    )
    op.create_index(
        "ix_financial_records_sap_doc_entry", "financial_records", ["sap_doc_entry"]
    )

    op.create_table(
        "orders",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("customer_id", sa.Integer(), sa.ForeignKey("customers.id"), nullable=False),
        sa.Column("sap_doc_entry", sa.Integer(), nullable=False),
        sa.Column("sap_doc_num", sa.String(30), nullable=True),
        sa.Column("order_date", sa.Date(), nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("total_consumption_at_analysis", sa.Numeric(18, 2), nullable=True),
        sa.Column("credit_limit_at_analysis", sa.Numeric(18, 2), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "em_analise",
                "aprovado",
                "aprovado_com_ressalva",
                "bloqueado",
                "rejeitado",
                name="order_status",
            ),
            nullable=False,
            server_default="em_analise",
        ),
        sa.Column("analyzed_at", sa.DateTime(), nullable=True),
        sa.Column("received_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("reviewed_by", sa.String(100), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.Column("review_notes", sa.String(500), nullable=True),
    )
    op.create_index("ix_orders_customer_id", "orders", ["customer_id"])
    op.create_index("ix_orders_sap_doc_entry", "orders", ["sap_doc_entry"], unique=True)

    op.create_table(
        "serasa_queries",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("customer_id", sa.Integer(), sa.ForeignKey("customers.id"), nullable=False),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id"), nullable=True),
        sa.Column("score", sa.Integer(), nullable=True),
        sa.Column("pefin_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("pefin_total_amount", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("refin_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("refin_total_amount", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("protests_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "protests_total_amount", sa.Numeric(18, 2), nullable=False, server_default="0"
        ),
        sa.Column("lawsuits_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("checks_returned_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("raw_response", sa.JSON(), nullable=True),
        sa.Column("queried_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_serasa_queries_customer_id", "serasa_queries", ["customer_id"])

    op.create_table(
        "credit_score_history",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("customer_id", sa.Integer(), sa.ForeignKey("customers.id"), nullable=False),
        sa.Column(
            "serasa_query_id", sa.Integer(), sa.ForeignKey("serasa_queries.id"), nullable=True
        ),
        sa.Column(
            "triggered_by_order_id", sa.Integer(), sa.ForeignKey("orders.id"), nullable=True
        ),
        sa.Column("default_probability", sa.Numeric(6, 5), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("model_version", sa.String(50), nullable=False),
        sa.Column("features_snapshot", sa.JSON(), nullable=True),
        sa.Column("computed_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index(
        "ix_credit_score_history_customer_id", "credit_score_history", ["customer_id"]
    )

    op.create_table(
        "credit_limit_history",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("customer_id", sa.Integer(), sa.ForeignKey("customers.id"), nullable=False),
        sa.Column(
            "score_history_id",
            sa.Integer(),
            sa.ForeignKey("credit_score_history.id"),
            nullable=True,
        ),
        sa.Column("calculated_limit", sa.Numeric(18, 2), nullable=False),
        sa.Column("rule_version", sa.String(50), nullable=False),
        sa.Column("manual_override_limit", sa.Numeric(18, 2), nullable=True),
        sa.Column("override_reason", sa.String(500), nullable=True),
        sa.Column("overridden_by", sa.String(100), nullable=True),
        sa.Column("computed_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index(
        "ix_credit_limit_history_customer_id", "credit_limit_history", ["customer_id"]
    )

    op.create_table(
        "sync_state",
        sa.Column("key", sa.String(100), primary_key=True),
        sa.Column("value", sa.String(100), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("sync_state")
    op.drop_table("credit_limit_history")
    op.drop_table("credit_score_history")
    op.drop_table("serasa_queries")
    op.drop_table("orders")
    op.drop_table("financial_records")
    op.drop_table("customers")
