"""W-08.7 watchlist/notes

Revision ID: 0007_collab
Revises: 0006_strategy
"""

from alembic import op
import sqlalchemy as sa

revision = "0007_collab"
down_revision = "0006_strategy"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "watchlist",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("app_user.id"), nullable=False),
        sa.Column("security_id", sa.String(length=36), sa.ForeignKey("security.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("user_id", "security_id", name="uq_watch"),
    )
    op.create_table(
        "note",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("app_user.id"), nullable=False),
        sa.Column("company_id", sa.String(length=36), sa.ForeignKey("company.id"), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("note")
    op.drop_table("watchlist")
