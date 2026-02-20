"""Procurement pipeline enhancements

Adds RequirementAction, enhances OpportunityTask, and adds editing features to Activity.
Also adds new fields to Requirement (Lead) and Opportunity models.

Revision ID: procurement_pipeline_enhancements
Revises: a051a75abf1f
Create Date: 2026-02-09 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'procurement_pipeline_enhancements'
down_revision = 'a051a75abf1f'
branch_labels = None
depends_on = None


def upgrade():
    # ### Add new columns to lead table (Requirement) ###
    # Note: 'name' will be added as nullable first, then we'll copy company_name to name, then make it non-nullable
    op.add_column('lead', sa.Column('name', sa.String(length=255), nullable=True))
    op.add_column('lead', sa.Column('requirement_type', sa.String(length=50), nullable=True))
    op.add_column('lead', sa.Column('priority', sa.String(length=20), server_default='Medium', nullable=True))
    op.add_column('lead', sa.Column('description', sa.Text(), nullable=True))
    op.add_column('lead', sa.Column('estimated_budget', sa.Float(), nullable=True))
    op.add_column('lead', sa.Column('currency', sa.String(length=3), server_default='EUR', nullable=True))
    op.add_column('lead', sa.Column('needed_by', sa.Date(), nullable=True))
    op.add_column('lead', sa.Column('created_by_id', sa.Integer(), nullable=True))
    op.add_column('lead', sa.Column('is_archived', sa.Boolean(), server_default='0', nullable=False))

    # Copy data from company_name to name and notes to description
    op.execute('UPDATE lead SET name = company_name WHERE name IS NULL')
    op.execute('UPDATE lead SET description = notes WHERE description IS NULL')

    # Make company_name nullable so new records don't require it
    # (SQLite doesn't support this easily, skip for SQLite)
    try:
        op.alter_column('lead', 'company_name', nullable=True)
    except:
        pass

    # Now make name non-nullable
    # Note: SQLite doesn't support ALTER COLUMN ... SET NOT NULL
    # Use try/except to handle SQLite vs PostgreSQL
    try:
        op.alter_column('lead', 'name', nullable=False)
    except:
        # SQLite: constraint enforced at application level
        pass

    # Add foreign keys (skip for SQLite, constraints enforced at app level)
    try:
        op.create_foreign_key('fk_lead_created_by', 'lead', 'user', ['created_by_id'], ['id'])
    except:
        pass

    # ### Add new columns to opportunity table ###
    op.add_column('opportunity', sa.Column('requirement_id', sa.Integer(), nullable=True))
    op.add_column('opportunity', sa.Column('risk_id', sa.Integer(), nullable=True))
    op.add_column('opportunity', sa.Column('budget_id', sa.Integer(), nullable=True))

    # Add foreign keys (skip for SQLite, constraints enforced at app level)
    try:
        op.create_foreign_key('fk_opportunity_requirement', 'opportunity', 'lead', ['requirement_id'], ['id'])
        op.create_foreign_key('fk_opportunity_risk', 'opportunity', 'risk', ['risk_id'], ['id'])
        op.create_foreign_key('fk_opportunity_budget', 'opportunity', 'budget', ['budget_id'], ['id'])
    except:
        pass

    # ### Add new columns to activity table ###
    op.add_column('activity', sa.Column('edited_at', sa.DateTime(), nullable=True))
    op.add_column('activity', sa.Column('is_hidden', sa.Boolean(), server_default='0', nullable=False))

    # ### Enhance opportunity_task table (if it exists) or create it ###
    # First, check if the table exists and needs updating
    try:
        # Try to add new columns (they might not exist from previous migration)
        op.add_column('opportunity_task', sa.Column('due_date', sa.Date(), nullable=True))
        op.add_column('opportunity_task', sa.Column('completed_at', sa.DateTime(), nullable=True))
        op.add_column('opportunity_task', sa.Column('is_hidden', sa.Boolean(), server_default='0', nullable=False))
    except:
        pass

    try:
        # Update description length if needed (not supported in SQLite)
        op.alter_column('opportunity_task', 'description', type_=sa.String(length=500))
    except:
        pass

    try:
        # Ensure is_completed has proper default (not supported in SQLite)
        op.alter_column('opportunity_task', 'is_completed', server_default='0', nullable=False)
    except:
        # Table doesn't exist or columns already exist, skip
        pass

    # ### Create requirement_action table ###
    op.create_table('requirement_action',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('requirement_id', sa.Integer(), nullable=False),
        sa.Column('action_type', sa.String(length=50), server_default='Note', nullable=True),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('edited_at', sa.DateTime(), nullable=True),
        sa.Column('is_hidden', sa.Boolean(), server_default='0', nullable=False),
        sa.Column('created_by_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['requirement_id'], ['lead.id'], ),
        sa.ForeignKeyConstraint(['created_by_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade():
    # ### Drop requirement_action table ###
    op.drop_table('requirement_action')

    # ### Remove columns from opportunity_task (if they exist) ###
    try:
        op.drop_column('opportunity_task', 'is_hidden')
        op.drop_column('opportunity_task', 'completed_at')
        op.drop_column('opportunity_task', 'due_date')
    except:
        pass

    # ### Remove columns from activity table ###
    op.drop_column('activity', 'is_hidden')
    op.drop_column('activity', 'edited_at')

    # ### Remove foreign keys and columns from opportunity table ###
    op.drop_constraint('fk_opportunity_budget', 'opportunity', type_='foreignkey')
    op.drop_constraint('fk_opportunity_risk', 'opportunity', type_='foreignkey')
    op.drop_constraint('fk_opportunity_requirement', 'opportunity', type_='foreignkey')
    op.drop_column('opportunity', 'budget_id')
    op.drop_column('opportunity', 'risk_id')
    op.drop_column('opportunity', 'requirement_id')

    # ### Remove columns from lead table ###
    op.drop_constraint('fk_lead_created_by', 'lead', type_='foreignkey')
    op.drop_column('lead', 'is_archived')
    op.drop_column('lead', 'created_by_id')
    op.drop_column('lead', 'needed_by')
    op.drop_column('lead', 'currency')
    op.drop_column('lead', 'estimated_budget')
    op.drop_column('lead', 'description')
    op.drop_column('lead', 'priority')
    op.drop_column('lead', 'requirement_type')
    op.drop_column('lead', 'name')
