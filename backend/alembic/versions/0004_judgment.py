"""W-08.4 judgment slot/revision

Revision ID: 0004_judgment
Revises: 0003_company
"""

from alembic import op
import sqlalchemy as sa

revision = "0004_judgment"
down_revision = "0003_company"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "judgment_slot",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("slot_key", sa.String(length=250), nullable=False),
        sa.Column("kind", sa.String(length=40), nullable=False),
        sa.Column("dimension", sa.String(length=80), nullable=True),
        sa.Column("effective_revision_id", sa.String(length=36), nullable=True),
        sa.Column("generation", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("slot_key", name="uq_slot_key"),
    )
    op.create_table(
        "judgment_revision",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("slot_id", sa.String(length=36), sa.ForeignKey("judgment_slot.id"), nullable=False),
        sa.Column("author_type", sa.String(length=20), nullable=False),
        sa.Column("value_json", sa.Text(), nullable=False),
        sa.Column("decision", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("judgment_revision")
    op.drop_table("judgment_slot")
