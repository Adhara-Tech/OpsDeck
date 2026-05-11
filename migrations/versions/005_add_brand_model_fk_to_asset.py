"""add_brand_model_fk_to_asset

Adds brand_id and model_id FK columns to asset. Keeps legacy brand/model
text columns in place — they will be backfilled in 007 and dropped in 008.

Revision ID: 005
Revises: 004
Create Date: 2026-04-13

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '005'
down_revision = '004'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('asset', schema=None) as batch_op:
        batch_op.add_column(sa.Column('brand_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('model_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            'fk_asset_brand_id', 'brand', ['brand_id'], ['id']
        )
        batch_op.create_foreign_key(
            'fk_asset_model_id', 'asset_model', ['model_id'], ['id']
        )
        batch_op.create_index('ix_asset_brand_id', ['brand_id'], unique=False)
        batch_op.create_index('ix_asset_model_id', ['model_id'], unique=False)


def downgrade():
    with op.batch_alter_table('asset', schema=None) as batch_op:
        batch_op.drop_index('ix_asset_model_id')
        batch_op.drop_index('ix_asset_brand_id')
        batch_op.drop_constraint('fk_asset_model_id', type_='foreignkey')
        batch_op.drop_constraint('fk_asset_brand_id', type_='foreignkey')
        batch_op.drop_column('model_id')
        batch_op.drop_column('brand_id')
