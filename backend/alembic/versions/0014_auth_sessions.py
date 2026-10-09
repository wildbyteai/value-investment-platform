"""real login: password hash on app_user, auth_session, login_attempt

Revision ID: 0014_auth_sessions
Revises: 0013_collectors_skills
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = '0014_auth_sessions'
down_revision: Union[str, Sequence[str], None] = '0013_collectors_skills'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('app_user', sa.Column('password_hash', sa.String(length=255), nullable=True))
    op.add_column('app_user', sa.Column('disabled', sa.Boolean(), server_default='false', nullable=False))
    op.create_table('auth_session',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('token_hash', sa.String(length=64), nullable=False),
    sa.Column('user_id', sa.String(length=36), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('last_seen_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('ip', sa.String(length=64), nullable=True),
    sa.Column('user_agent', sa.String(length=300), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['app_user.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('token_hash')
    )
    op.create_index(op.f('ix_auth_session_user_id'), 'auth_session', ['user_id'], unique=False)
    op.create_table('login_attempt',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('login', sa.String(length=120), nullable=False),
    sa.Column('ip', sa.String(length=64), nullable=True),
    sa.Column('success', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_login_attempt_created_at'), 'login_attempt', ['created_at'], unique=False)
    op.create_index(op.f('ix_login_attempt_ip'), 'login_attempt', ['ip'], unique=False)
    op.create_index(op.f('ix_login_attempt_login'), 'login_attempt', ['login'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_login_attempt_login'), table_name='login_attempt')
    op.drop_index(op.f('ix_login_attempt_ip'), table_name='login_attempt')
    op.drop_index(op.f('ix_login_attempt_created_at'), table_name='login_attempt')
    op.drop_table('login_attempt')
    op.drop_index(op.f('ix_auth_session_user_id'), table_name='auth_session')
    op.drop_table('auth_session')
    op.drop_column('app_user', 'disabled')
    op.drop_column('app_user', 'password_hash')
