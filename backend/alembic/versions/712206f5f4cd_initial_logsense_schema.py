"""initial_logsense_schema

Revision ID: 712206f5f4cd
Revises: 
Create Date: 2026-09-24 10:54:24.021398

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '712206f5f4cd'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create the initial LogSense application schema."""
    op.create_table(
        'logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('source_host', sa.String(length=100), nullable=False),
        sa.Column('log_level', sa.String(length=20), nullable=False),
        sa.Column('raw_message', sa.Text(), nullable=False),
        sa.Column('template_id', sa.Integer(), nullable=True),
        sa.Column('parsed_template', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_logs_log_level'), 'logs', ['log_level'], unique=False)
    op.create_index(op.f('ix_logs_source_host'), 'logs', ['source_host'], unique=False)
    op.create_index(op.f('ix_logs_template_id'), 'logs', ['template_id'], unique=False)
    op.create_index(op.f('ix_logs_timestamp'), 'logs', ['timestamp'], unique=False)

    op.create_table(
        'incidents',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('severity', sa.String(length=20), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='OPEN'),
        sa.Column('trigger_log_id', sa.Integer(), nullable=True),
        sa.Column('gemini_rca', sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(['trigger_log_id'], ['logs.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_incidents_created_at'), 'incidents', ['created_at'], unique=False)
    op.create_index(op.f('ix_incidents_severity'), 'incidents', ['severity'], unique=False)
    op.create_index(op.f('ix_incidents_status'), 'incidents', ['status'], unique=False)

    op.create_table(
        'runbooks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('category', sa.String(length=100), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_runbooks_category'), 'runbooks', ['category'], unique=False)
    op.create_index(op.f('ix_runbooks_created_at'), 'runbooks', ['created_at'], unique=False)


def downgrade() -> None:
    """Drop the initial LogSense schema."""
    op.drop_index(op.f('ix_runbooks_created_at'), table_name='runbooks')
    op.drop_index(op.f('ix_runbooks_category'), table_name='runbooks')
    op.drop_table('runbooks')

    op.drop_index(op.f('ix_incidents_status'), table_name='incidents')
    op.drop_index(op.f('ix_incidents_severity'), table_name='incidents')
    op.drop_index(op.f('ix_incidents_created_at'), table_name='incidents')
    op.drop_table('incidents')

    op.drop_index(op.f('ix_logs_timestamp'), table_name='logs')
    op.drop_index(op.f('ix_logs_template_id'), table_name='logs')
    op.drop_index(op.f('ix_logs_source_host'), table_name='logs')
    op.drop_index(op.f('ix_logs_log_level'), table_name='logs')
    op.drop_table('logs')
