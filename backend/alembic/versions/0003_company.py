"""W-08.3 company/security/link/fact

Revision ID: 0003_company
Revises: 0002_intake
"""

from alembic import op
import sqlalchemy as sa

revision = "0003_company"
down_revision = "0002_intake"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "company",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("name", sa.String(length=200), nullable=False, unique=True),
        sa.Column("industry_key", sa.String(length=80), nullable=False, server_default="manufacturing"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "security",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("company_id", sa.String(length=36), sa.ForeignKey("company.id"), nullable=False),
        sa.Column("market", sa.String(length=20), nullable=False),
        sa.Column("ticker", sa.String(length=30), nullable=False),
        sa.Column("currency", sa.String(length=10), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("market", "ticker", name="uq_security_market_ticker"),
    )
    op.create_table(
        "item_company_link",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("item_id", sa.String(length=36), sa.ForeignKey("information_item.id"), nullable=False),
        sa.Column("company_id", sa.String(length=36), sa.ForeignKey("company.id"), nullable=True),
        sa.Column("label_text", sa.String(length=200), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("relevance", sa.Numeric(12, 6), nullable=True),
        sa.Column("confidence", sa.Numeric(12, 6), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("item_id", "company_id", name="uq_link_item_company"),
    )
    op.create_table(
        "economic_fact",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("company_id", sa.String(length=36), sa.ForeignKey("company.id"), nullable=False),
        sa.Column("fact_key", sa.String(length=200), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("economic_fact")
    op.drop_table("item_company_link")
    op.drop_table("security")
    op.drop_table("company")
