"""Add website field to supplier

Revision ID: add_website_to_supplier
Revises: make_subscription_supplier_nullable
Create Date: 2026-03-10

"""
from alembic import op
import sqlalchemy as sa

revision = 'add_website_to_supplier'
down_revision = 'make_subscription_supplier_nullable'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('supplier', sa.Column('website', sa.String(255), nullable=True))


def downgrade():
    op.drop_column('supplier', 'website')
