"""add_notes_to_onboarding_process

Adds a nullable `notes` text column to the onboarding_process table.

Revision ID: 009
Revises: 008
Create Date: 2026-05-13

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '009'
down_revision = '008'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('onboarding_process', sa.Column('notes', sa.Text(), nullable=True))


def downgrade():
    op.drop_column('onboarding_process', 'notes')
