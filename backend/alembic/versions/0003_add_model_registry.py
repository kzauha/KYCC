"""Add model registry and experiments tables for ML training

Revision ID: 0003_add_model_registry
Revises: 0002_add_ground_truth_labels
Create Date: 2025-12-14
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0003_add_model_registry'
down_revision = '0002_add_ground_truth_labels'
branch_labels = None
depends_on = None


def upgrade():
    """Create model_registry and model_experiments tables."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_names = set(inspector.get_table_names())
    
    # Create model_registry table if it doesn't exist
    if 'model_registry' not in table_names:
        op.create_table(
            'model_registry',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('model_name', sa.String(50), nullable=False),
            sa.Column('model_version', sa.String(50), nullable=False),
            sa.Column('algorithm_config', sa.JSON(), nullable=False),
            sa.Column('training_data_batch_id', sa.String(100), nullable=False),
            sa.Column('training_date', sa.DateTime(), default=sa.func.now(), nullable=False),
            sa.Column('performance_metrics', sa.JSON(), nullable=False),
            sa.Column('is_active', sa.Integer(), default=0, nullable=False),
            sa.Column('deployed_at', sa.DateTime(), nullable=True),
            sa.Column('rollback_available_to', sa.Integer(), sa.ForeignKey('model_registry.id'), nullable=True),
            sa.Column('created_at', sa.DateTime(), default=sa.func.now(), nullable=False),
        )
        
        # Create indexes
        op.create_index(op.f('ix_model_registry_id'), 'model_registry', ['id'], unique=True)
        op.create_index(op.f('ix_model_registry_training_data_batch_id'), 'model_registry', ['training_data_batch_id'], unique=False)
        op.create_index('idx_model_name_version', 'model_registry', ['model_name', 'model_version'], unique=True)
    
    # Create model_experiments table if it doesn't exist
    if 'model_experiments' not in table_names:
        op.create_table(
            'model_experiments',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('experiment_name', sa.String(100), nullable=False),
            sa.Column('algorithm', sa.String(50), nullable=False),
            sa.Column('hyperparameters', sa.JSON(), nullable=False),
            sa.Column('cv_scores', sa.JSON(), nullable=False),
            sa.Column('mean_cv_score', sa.Float(), nullable=False),
            sa.Column('std_cv_score', sa.Float(), nullable=False),
            sa.Column('training_time_seconds', sa.Float(), nullable=False),
            sa.Column('created_at', sa.DateTime(), default=sa.func.now(), nullable=False),
            sa.Column('notes', sa.Text(), nullable=True),
        )
        
        # Create indexes
        op.create_index(op.f('ix_model_experiments_id'), 'model_experiments', ['id'], unique=True)
        op.create_index(op.f('ix_model_experiments_experiment_name'), 'model_experiments', ['experiment_name'], unique=False)


def downgrade():
    """Drop model_registry and model_experiments tables."""
    # Drop model_experiments first (no foreign keys)
    op.drop_index(op.f('ix_model_experiments_experiment_name'), table_name='model_experiments')
    op.drop_index(op.f('ix_model_experiments_id'), table_name='model_experiments')
    op.drop_table('model_experiments')
    
    # Drop model_registry (has self-referencing foreign key)
    op.drop_index('idx_model_name_version', table_name='model_registry')
    op.drop_index(op.f('ix_model_registry_training_data_batch_id'), table_name='model_registry')
    op.drop_index(op.f('ix_model_registry_id'), table_name='model_registry')
    op.drop_table('model_registry')
