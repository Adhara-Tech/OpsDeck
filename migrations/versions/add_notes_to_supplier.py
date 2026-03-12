"""Add notes field to supplier

Revision ID: add_notes_to_supplier
Revises: add_website_to_supplier
Create Date: 2026-03-10

"""
from alembic import op
import sqlalchemy as sa

revision = 'add_notes_to_supplier'
down_revision = 'add_website_to_supplier'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('supplier', sa.Column('notes', sa.Text(), nullable=True))


def downgrade():
    op.drop_column('supplier', 'notes')
