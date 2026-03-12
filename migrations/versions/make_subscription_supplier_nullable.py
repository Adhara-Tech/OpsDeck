"""Make subscription.supplier_id nullable

Revision ID: make_subscription_supplier_nullable
Revises: add_is_critical_to_supplier
Create Date: 2026-03-09

"""
from alembic import op
import sqlalchemy as sa

revision = 'make_subscription_supplier_nullable'
down_revision = 'add_is_critical_to_supplier'
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column('subscription', 'supplier_id', nullable=True)


def downgrade():
    op.alter_column('subscription', 'supplier_id', nullable=False)
