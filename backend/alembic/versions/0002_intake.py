"""W-08.2 intake tables

Revision ID: 0002_intake
Revises: 0001_initial
Create Date: 2026-10-01
"""

from alembic import op
import sqlalchemy as sa

revision = "0002_intake"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "source_registry",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("source_key", sa.String(length=120), nullable=False, unique=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("policy_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "information_item",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("source_id", sa.String(length=36), sa.ForeignKey("source_registry.id"), nullable=False),
        sa.Column("entry_key", sa.String(length=120), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("content_kind", sa.String(length=40), nullable=False),
        sa.Column("summary_text", sa.Text(), nullable=True),
        sa.Column("reading_metadata_json", sa.Text(), nullable=False),
        sa.Column("publication_json", sa.Text(), nullable=False),
        sa.Column("origin_locator_json", sa.Text(), nullable=True),
        sa.Column("observed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("body_state", sa.String(length=40), nullable=False, server_default="no_locator"),
        sa.Column("body_url", sa.Text(), nullable=True),
        sa.UniqueConstraint("source_id", "entry_key", name="uq_item_source_entry"),
    )
    op.create_table(
        "item_source_ref",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("item_id", sa.String(length=36), sa.ForeignKey("information_item.id"), nullable=False),
        sa.Column("reference_key", sa.String(length=40), nullable=False),
        sa.Column("source_name", sa.String(length=200), nullable=False),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("locator_kind", sa.String(length=40), nullable=False, server_default="unknown"),
        sa.Column("source_locator_json", sa.Text(), nullable=True),
        sa.Column("access_state", sa.String(length=40), nullable=False, server_default="not_acquired"),
    )
    # extend ingestion_run with manifest / result columns
    op.add_column("ingestion_run", sa.Column("input_manifest_hash", sa.String(length=64), nullable=True))
    op.add_column("ingestion_run", sa.Column("output_json", sa.Text(), nullable=True))
    op.add_column("ingestion_run", sa.Column("upstream_generated_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("ingestion_run", "upstream_generated_at")
    op.drop_column("ingestion_run", "output_json")
    op.drop_column("ingestion_run", "input_manifest_hash")
    op.drop_table("item_source_ref")
    op.drop_table("information_item")
    op.drop_table("source_registry")
