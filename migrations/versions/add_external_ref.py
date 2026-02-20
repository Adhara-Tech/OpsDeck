"""Add external_ref to change, security_incident, onboarding_process

Revision ID: add_external_ref
Revises: add_missing_indexes
Create Date: 2026-02-19

"""
from alembic import op
import sqlalchemy as sa

revision = 'add_external_ref'
down_revision = 'add_missing_indexes'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('change', sa.Column('external_ref', sa.String(length=255), nullable=True))
    op.create_index('ix_change_external_ref', 'change', ['external_ref'], unique=True)

    op.add_column('security_incident', sa.Column('external_ref', sa.String(length=255), nullable=True))
    op.create_index('ix_security_incident_external_ref', 'security_incident', ['external_ref'], unique=True)

    op.add_column('onboarding_process', sa.Column('external_ref', sa.String(length=255), nullable=True))
    op.create_index('ix_onboarding_process_external_ref', 'onboarding_process', ['external_ref'], unique=True)


def downgrade():
    op.drop_index('ix_onboarding_process_external_ref', table_name='onboarding_process')
    op.drop_column('onboarding_process', 'external_ref')
    op.drop_index('ix_security_incident_external_ref', table_name='security_incident')
    op.drop_column('security_incident', 'external_ref')
    op.drop_index('ix_change_external_ref', table_name='change')
    op.drop_column('change', 'external_ref')
