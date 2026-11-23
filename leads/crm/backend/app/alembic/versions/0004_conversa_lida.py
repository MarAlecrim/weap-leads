"""Caixa de conversas: até onde cada usuário leu

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-23
"""

import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "crm_conversa_lida",
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey("user.id", ondelete="CASCADE"),
            primary_key=True,
            nullable=False,
        ),
        sa.Column("chave", sa.String(length=20), primary_key=True, nullable=False),
        sa.Column("ate_id", sa.BigInteger(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("crm_conversa_lida")
