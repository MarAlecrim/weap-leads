"""Perfis de usuário e funil (kanban)

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-20
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("user", sa.Column("perfil", sa.String(length=20), nullable=False, server_default="vendedor"))
    op.add_column(
        "user",
        sa.Column("numeros", postgresql.ARRAY(sa.String()), nullable=False, server_default="{}"),
    )
    op.execute("""UPDATE "user" SET perfil = 'admin' WHERE is_superuser""")

    op.create_table(
        "crm_negocio",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("chave", sa.String(length=20), nullable=False),
        sa.Column("telefone", sa.String(length=40), nullable=True),
        sa.Column("nome", sa.String(length=255), nullable=False),
        sa.Column("cnpj", sa.String(length=14), nullable=True),
        sa.Column("cidade", sa.String(length=120), nullable=True),
        sa.Column("origem", sa.String(length=20), nullable=False),
        sa.Column("nota", sa.Integer(), nullable=True),
        sa.Column("instancia", sa.String(length=120), nullable=True),
        sa.Column("etapa", sa.String(length=20), nullable=False),
        sa.Column("etapa_desde", sa.DateTime(timezone=True), nullable=False),
        sa.Column("movido_manual", sa.Boolean(), nullable=False),
        sa.Column("status_agente", sa.String(length=40), nullable=True),
        sa.Column("ia_pausada", sa.Boolean(), nullable=False),
        sa.Column("valor_cents", sa.Integer(), nullable=True),
        sa.Column("servico", sa.String(length=40), nullable=True),
        sa.Column("responsavel_id", sa.Uuid(), sa.ForeignKey("user.id", ondelete="SET NULL"), nullable=True),
        sa.Column("perdido_motivo", sa.String(length=120), nullable=True),
        sa.Column("proxima_acao", sa.String(length=255), nullable=True),
        sa.Column("proxima_acao_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ultimo_contato_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ultima_resposta_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("atualizado_em", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_crm_negocio_chave", "crm_negocio", ["chave"], unique=True)
    op.create_index("ix_crm_negocio_etapa", "crm_negocio", ["etapa"])
    op.create_index("ix_crm_negocio_instancia", "crm_negocio", ["instancia"])
    op.create_index("ix_crm_negocio_responsavel_id", "crm_negocio", ["responsavel_id"])

    op.create_table(
        "crm_negocio_historico",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "negocio_id", sa.Integer(), sa.ForeignKey("crm_negocio.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("de", sa.String(length=20), nullable=True),
        sa.Column("para", sa.String(length=20), nullable=False),
        sa.Column("autor", sa.String(length=255), nullable=False),
        sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_crm_negocio_historico_negocio_id", "crm_negocio_historico", ["negocio_id"])


def downgrade() -> None:
    op.drop_table("crm_negocio_historico")
    op.drop_table("crm_negocio")
    op.drop_column("user", "numeros")
    op.drop_column("user", "perfil")
