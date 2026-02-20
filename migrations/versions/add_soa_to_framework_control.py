"""Add SOA fields (is_applicable, soa_justification) to framework_control

Revision ID: add_soa_to_framework_control
Revises: add_external_ref
Create Date: 2026-02-20

"""
from alembic import op
import sqlalchemy as sa

revision = 'add_soa_to_framework_control'
down_revision = 'add_external_ref'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('framework_control', sa.Column('is_applicable', sa.Boolean(), nullable=False, server_default=sa.text('1')))
    op.add_column('framework_control', sa.Column('soa_justification', sa.Text(), nullable=True))


def downgrade():
    op.drop_column('framework_control', 'soa_justification')
    op.drop_column('framework_control', 'is_applicable')
