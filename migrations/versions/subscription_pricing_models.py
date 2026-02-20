"""Add pricing model support to subscriptions

Adds support for fixed and per-user pricing models to subscriptions,
with enhanced cost history tracking.

Revision ID: subscription_pricing_models
Revises: procurement_pipeline_enhancements
Create Date: 2026-02-13 15:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'subscription_pricing_models'
down_revision = 'procurement_pipeline_enhancements'
branch_labels = None
depends_on = None


def upgrade():
    # Add new columns to subscription table
    op.add_column('subscription', sa.Column('pricing_model', sa.String(length=20), server_default='fixed', nullable=True))
    op.add_column('subscription', sa.Column('cost_per_user', sa.Float(), nullable=True))

    # Update existing subscriptions to use fixed pricing model
    op.execute("UPDATE subscription SET pricing_model = 'fixed' WHERE pricing_model IS NULL")

    # Add new tracking columns to cost_history table
    op.add_column('cost_history', sa.Column('pricing_model', sa.String(length=20), nullable=True))
    op.add_column('cost_history', sa.Column('cost_per_user', sa.Float(), nullable=True))
    op.add_column('cost_history', sa.Column('user_count', sa.Integer(), nullable=True))
    op.add_column('cost_history', sa.Column('reason', sa.String(length=50), nullable=True))

    # Populate cost_history with pricing_model for existing entries
    op.execute("UPDATE cost_history SET pricing_model = 'fixed' WHERE pricing_model IS NULL")


def downgrade():
    # Remove columns from cost_history
    op.drop_column('cost_history', 'reason')
    op.drop_column('cost_history', 'user_count')
    op.drop_column('cost_history', 'cost_per_user')
    op.drop_column('cost_history', 'pricing_model')

    # Remove columns from subscription
    op.drop_column('subscription', 'cost_per_user')
    op.drop_column('subscription', 'pricing_model')
