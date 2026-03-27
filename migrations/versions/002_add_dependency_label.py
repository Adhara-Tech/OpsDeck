"""add_dependency_label

Revision ID: 002
Revises: 001
Create Date: 2026-03-27

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('service_dependencies',
        sa.Column('label', sa.String(length=20), nullable=True)
    )


def downgrade():
    op.drop_column('service_dependencies', 'label')
