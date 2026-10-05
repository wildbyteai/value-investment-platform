"""W-08.6 strategy state machine

Revision ID: 0006_strategy
Revises: 0004_judgment
"""

from alembic import op
import sqlalchemy as sa

revision = "0006_strategy"
down_revision = "0004_judgment"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "strategy_version",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("strategy_key", sa.String(length=80), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("rules_json", sa.Text(), nullable=False),
        sa.Column("published", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("strategy_key", "version", name="uq_strategy_key_version"),
    )
    op.create_table(
        "security_state",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("security_id", sa.String(length=36), sa.ForeignKey("security.id"), nullable=False),
        sa.Column("strategy_id", sa.String(length=36), sa.ForeignKey("strategy_version.id"), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="OUT"),
        sa.Column("pending_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_confirmed", sa.String(length=30), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("security_id", "strategy_id", name="uq_state_security_strategy"),
    )
    op.create_table(
        "change_record",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("security_id", sa.String(length=36), nullable=False),
        sa.Column("strategy_id", sa.String(length=36), nullable=False),
        sa.Column("session_label", sa.String(length=40), nullable=False),
        sa.Column("from_status", sa.String(length=30), nullable=False),
        sa.Column("to_status", sa.String(length=30), nullable=False),
        sa.Column("reason", sa.String(length=120), nullable=False),
        sa.Column("delivery_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("change_record")
    op.drop_table("security_state")
    op.drop_table("strategy_version")
