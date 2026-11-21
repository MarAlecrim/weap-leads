"""Notas nos cards do funil

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-21
"""

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "crm_negocio_nota",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "negocio_id", sa.Integer(), sa.ForeignKey("crm_negocio.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("autor", sa.String(length=255), nullable=False),
        sa.Column("texto", sa.String(length=4000), nullable=False),
        sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_crm_negocio_nota_negocio_id", "crm_negocio_nota", ["negocio_id"])


def downgrade() -> None:
    op.drop_table("crm_negocio_nota")
