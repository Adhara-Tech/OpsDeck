"""Add is_critical field to supplier

Revision ID: add_is_critical_to_supplier
Revises: add_soa_to_framework_control
Create Date: 2026-03-09

"""
from alembic import op
import sqlalchemy as sa

revision = 'add_is_critical_to_supplier'
down_revision = 'add_soa_to_framework_control'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('supplier', sa.Column('is_critical', sa.Boolean(), nullable=True, server_default=sa.text('false')))


def downgrade():
    op.drop_column('supplier', 'is_critical')
