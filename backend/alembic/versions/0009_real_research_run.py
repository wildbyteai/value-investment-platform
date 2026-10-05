"""Append immutable local research previews; existing rows are untouched."""
from alembic import op
import sqlalchemy as sa
revision='0009_real_research_run'
down_revision='8aab1c46fe7b'
branch_labels=None
depends_on=None

def upgrade():
    op.create_table('research_run',
        sa.Column('id',sa.String(36),primary_key=True),
        sa.Column('workspace_id',sa.String(36),sa.ForeignKey('workspace.id'),nullable=False),
        sa.Column('actor_id',sa.String(36),sa.ForeignKey('app_user.id'),nullable=False),
        sa.Column('command_key',sa.String(240),nullable=False),
        sa.Column('request_hash',sa.String(64),nullable=False),
        sa.Column('manifest_json',sa.Text(),nullable=False),
        sa.Column('manifest_hash',sa.String(64),nullable=False),
        sa.Column('result_json',sa.Text(),nullable=False),
        sa.Column('status',sa.String(40),nullable=False),
        sa.Column('created_at',sa.DateTime(timezone=True),server_default=sa.text('now()'),nullable=False),
        sa.UniqueConstraint('workspace_id','command_key',name='uq_research_run_command'))

def downgrade():
    op.drop_table('research_run')
