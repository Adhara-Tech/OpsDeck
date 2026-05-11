"""create_asset_model_table

Revision ID: 004
Revises: 003
Create Date: 2026-04-13

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'asset_model',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('brand_id', sa.Integer(), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['brand_id'], ['brand.id'], name='fk_asset_model_brand_id'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('brand_id', 'name', name='uq_asset_model_brand_name'),
    )
    with op.batch_alter_table('asset_model', schema=None) as batch_op:
        batch_op.create_index('ix_asset_model_brand_id', ['brand_id'], unique=False)


def downgrade():
    with op.batch_alter_table('asset_model', schema=None) as batch_op:
        batch_op.drop_index('ix_asset_model_brand_id')
    op.drop_table('asset_model')
