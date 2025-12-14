"""Add ground truth labels table for ML training data

Revision ID: 0002_add_ground_truth_labels
Revises: 0001_add_accounts_and_batch
Create Date: 2025-12-14
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0002_add_ground_truth_labels'
down_revision = '0001_add_accounts_and_batch'
branch_labels = None
depends_on = None


def upgrade():
    """Create ground_truth_labels table."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_names = set(inspector.get_table_names())
    
    # Create ground_truth_labels table if it doesn't exist
    if 'ground_truth_labels' not in table_names:
        op.create_table(
            'ground_truth_labels',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('party_id', sa.Integer(), sa.ForeignKey('parties.id'), nullable=False, unique=True),
            sa.Column('will_default', sa.Integer(), nullable=False),
            sa.Column('risk_level', sa.String(20), nullable=False),
            sa.Column('label_source', sa.String(50), nullable=False),
            sa.Column('label_confidence', sa.Float(), default=1.0, nullable=True),
            sa.Column('reason', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(), default=sa.func.now(), nullable=False),
            sa.Column('dataset_batch', sa.String(100), nullable=False),
        )
        
        # Create indexes
        op.create_index(op.f('ix_ground_truth_labels_id'), 'ground_truth_labels', ['id'], unique=True)
        op.create_index(op.f('ix_ground_truth_labels_party_id'), 'ground_truth_labels', ['party_id'], unique=True)
        op.create_index(op.f('ix_ground_truth_labels_dataset_batch'), 'ground_truth_labels', ['dataset_batch'], unique=False)


def downgrade():
    """Drop ground_truth_labels table."""
    # Drop indexes
    op.drop_index(op.f('ix_ground_truth_labels_dataset_batch'), table_name='ground_truth_labels')
    op.drop_index(op.f('ix_ground_truth_labels_party_id'), table_name='ground_truth_labels')
    op.drop_index(op.f('ix_ground_truth_labels_id'), table_name='ground_truth_labels')
    
    # Drop table
    op.drop_table('ground_truth_labels')
