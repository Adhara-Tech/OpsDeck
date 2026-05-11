"""drop_legacy_brand_model_columns

Drops the legacy free-text `brand` and `model` columns from asset and
the legacy `brand` column from peripheral. Run only after 007 has been
validated and the application is reading/writing the new FK columns.

Revision ID: 008
Revises: 007
Create Date: 2026-04-13

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '008'
down_revision = '007'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('asset', schema=None) as batch_op:
        batch_op.drop_column('model')
        batch_op.drop_column('brand')
    with op.batch_alter_table('peripheral', schema=None) as batch_op:
        batch_op.drop_column('brand')


def downgrade():
    with op.batch_alter_table('asset', schema=None) as batch_op:
        batch_op.add_column(sa.Column('brand', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('model', sa.String(length=100), nullable=True))
    with op.batch_alter_table('peripheral', schema=None) as batch_op:
        batch_op.add_column(sa.Column('brand', sa.String(length=100), nullable=True))
