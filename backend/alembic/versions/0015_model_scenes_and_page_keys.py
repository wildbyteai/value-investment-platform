"""model scenes (llm_scene_binding) and page-saved encrypted API keys on llm_provider

Revision ID: 0015_model_scenes_keys
Revises: 0014_auth_sessions
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = '0015_model_scenes_keys'
down_revision: Union[str, Sequence[str], None] = '0014_auth_sessions'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('llm_provider', sa.Column('api_key_ciphertext', sa.Text(), nullable=True))
    op.add_column('llm_provider', sa.Column('api_key_hint', sa.String(length=8), nullable=True))
    op.alter_column('llm_provider', 'api_key_env', existing_type=sa.String(length=120), nullable=True)
    op.create_table('llm_scene_binding',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('workspace_id', sa.String(length=36), nullable=False),
    sa.Column('scene_key', sa.String(length=60), nullable=False),
    sa.Column('provider_id', sa.String(length=36), nullable=False),
    sa.Column('updated_by', sa.String(length=36), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['provider_id'], ['llm_provider.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('workspace_id', 'scene_key', name='uq_llm_scene_binding')
    )


def downgrade() -> None:
    op.drop_table('llm_scene_binding')
    # Page-saved keys cannot be kept by the old schema: they are dropped, and rows that only had a
    # page key get a placeholder variable name (the model then reports 未配置模型密钥 until fixed).
    op.execute("UPDATE llm_provider SET api_key_env = 'VIP_UNSET_API_KEY' WHERE api_key_env IS NULL")
    op.alter_column('llm_provider', 'api_key_env', existing_type=sa.String(length=120), nullable=False)
    op.drop_column('llm_provider', 'api_key_hint')
    op.drop_column('llm_provider', 'api_key_ciphertext')
