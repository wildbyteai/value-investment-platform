"""collectors and skills: scheduled LLM news collectors, maintainable skills, model search mode

Revision ID: 0013_collectors_skills
Revises: 0012_alerts
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = '0013_collectors_skills'
down_revision: Union[str, Sequence[str], None] = '0012_alerts'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('llm_provider', sa.Column('search_mode', sa.String(length=30), server_default='none', nullable=False))
    op.create_table('agent_skill',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('workspace_id', sa.String(length=36), nullable=False),
    sa.Column('skill_key', sa.String(length=80), nullable=False),
    sa.Column('name', sa.String(length=200), nullable=False),
    sa.Column('description', sa.Text(), nullable=False),
    sa.Column('body', sa.Text(), nullable=False),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.Column('enabled', sa.Boolean(), nullable=False),
    sa.Column('updated_by', sa.String(length=36), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('workspace_id', 'skill_key', name='uq_agent_skill_key')
    )
    op.create_table('collector_task',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('workspace_id', sa.String(length=36), nullable=False),
    sa.Column('name', sa.String(length=200), nullable=False),
    sa.Column('prompt', sa.Text(), nullable=False),
    sa.Column('provider_id', sa.String(length=36), nullable=True),
    sa.Column('skill_id', sa.String(length=36), nullable=True),
    sa.Column('feed_id', sa.String(length=36), nullable=False),
    sa.Column('schedule_json', sa.Text(), nullable=False),
    sa.Column('enabled', sa.Boolean(), nullable=False),
    sa.Column('next_run_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('last_run_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('last_status', sa.String(length=300), nullable=True),
    sa.Column('created_by', sa.String(length=36), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['feed_id'], ['news_feed.id'], ),
    sa.ForeignKeyConstraint(['provider_id'], ['llm_provider.id'], ),
    sa.ForeignKeyConstraint(['skill_id'], ['agent_skill.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_collector_task_workspace_id'), 'collector_task', ['workspace_id'], unique=False)
    op.create_index(op.f('ix_collector_task_next_run_at'), 'collector_task', ['next_run_at'], unique=False)
    op.create_table('collector_run',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('workspace_id', sa.String(length=36), nullable=False),
    sa.Column('task_id', sa.String(length=36), nullable=False),
    sa.Column('trigger', sa.String(length=20), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('model', sa.String(length=200), nullable=True),
    sa.Column('search_mode', sa.String(length=30), nullable=True),
    sa.Column('skill_key', sa.String(length=80), nullable=True),
    sa.Column('skill_version', sa.Integer(), nullable=True),
    sa.Column('items_found', sa.Integer(), nullable=False),
    sa.Column('stats_json', sa.Text(), nullable=False),
    sa.Column('error', sa.String(length=1000), nullable=True),
    sa.Column('output_excerpt', sa.Text(), nullable=False),
    sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['task_id'], ['collector_task.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_collector_run_task_id'), 'collector_run', ['task_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_collector_run_task_id'), table_name='collector_run')
    op.drop_table('collector_run')
    op.drop_index(op.f('ix_collector_task_next_run_at'), table_name='collector_task')
    op.drop_index(op.f('ix_collector_task_workspace_id'), table_name='collector_task')
    op.drop_table('collector_task')
    op.drop_table('agent_skill')
    op.drop_column('llm_provider', 'search_mode')
