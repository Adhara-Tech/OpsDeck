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


dependency_type = sa.Enum(
    'hosts', 'authenticates', 'provides_access', 'stores_data',
    'processes_data', 'monitors', 'backs_up', 'routes_traffic',
    'calls_api', 'sends_data',
    name='dependencytype',
)


def upgrade():
    dependency_type.create(op.get_bind(), checkfirst=True)
    op.add_column('service_dependencies',
        sa.Column('label', dependency_type, nullable=True)
    )


def downgrade():
    op.drop_column('service_dependencies', 'label')
    dependency_type.drop(op.get_bind(), checkfirst=True)
