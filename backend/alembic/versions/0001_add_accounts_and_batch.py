"""Add accounts table and batch/external tracking columns

Revision ID: 0001_add_accounts_and_batch
Revises: 
Create Date: 2025-12-12
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0001_add_accounts_and_batch'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_names = set(inspector.get_table_names())

    # Add columns to parties if table exists and missing columns
    if 'parties' in table_names:
        existing_party_cols = {c['name'] for c in inspector.get_columns('parties')}
        if 'external_id' not in existing_party_cols:
            op.add_column('parties', sa.Column('external_id', sa.String(), nullable=True))
            op.create_index(op.f('ix_parties_external_id'), 'parties', ['external_id'], unique=True)
        if 'batch_id' not in existing_party_cols:
            op.add_column('parties', sa.Column('batch_id', sa.String(), nullable=True))
            op.create_index(op.f('ix_parties_batch_id'), 'parties', ['batch_id'], unique=False)

    # Add batch_id/account_id to transactions if table exists and missing columns
    if 'transactions' in table_names:
        existing_tx_cols = {c['name'] for c in inspector.get_columns('transactions')}
        if 'batch_id' not in existing_tx_cols:
            op.add_column('transactions', sa.Column('batch_id', sa.String(), nullable=True))
        if 'account_id' not in existing_tx_cols:
            op.add_column('transactions', sa.Column('account_id', sa.Integer(), nullable=True))

    # Add batch_id to relationships if table exists and missing columns
    if 'relationships' in table_names:
        existing_rel_cols = {c['name'] for c in inspector.get_columns('relationships')}
        if 'batch_id' not in existing_rel_cols:
            op.add_column('relationships', sa.Column('batch_id', sa.String(), nullable=True))

    # Create accounts table if missing
    if 'accounts' not in table_names:
        op.create_table(
            'accounts',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('external_id', sa.String(), nullable=True),
            sa.Column('batch_id', sa.String(), nullable=True),
            sa.Column('party_id', sa.Integer(), sa.ForeignKey('parties.id'), nullable=False),
            sa.Column('account_number', sa.String(), nullable=False),
            sa.Column('account_type', sa.String(), nullable=True),
            sa.Column('currency', sa.String(), nullable=True),
            sa.Column('balance', sa.Float(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
        )
        op.create_index(op.f('ix_accounts_external_id'), 'accounts', ['external_id'], unique=False)
        op.create_index(op.f('ix_accounts_batch_id'), 'accounts', ['batch_id'], unique=False)
        op.create_index(op.f('ix_accounts_id'), 'accounts', ['id'], unique=True)

    # Add FK from transactions.account_id -> accounts.id (if transactions table exists and FK not present)
    if 'transactions' in table_names:
        fks = [fk['name'] for fk in inspector.get_foreign_keys('transactions')]
        if 'fk_transactions_account' not in fks:
            op.create_foreign_key(
                'fk_transactions_account',
                source_table='transactions',
                referent_table='accounts',
                local_cols=['account_id'],
                remote_cols=['id'],
            )


def downgrade():
    # Drop FK and columns from transactions
    op.drop_constraint('fk_transactions_account', 'transactions', type_='foreignkey')
    op.drop_column('transactions', 'account_id')
    op.drop_column('transactions', 'batch_id')

    # Drop relationships batch_id
    op.drop_column('relationships', 'batch_id')

    # Drop accounts table
    op.drop_index(op.f('ix_accounts_id'), table_name='accounts')
    op.drop_index(op.f('ix_accounts_batch_id'), table_name='accounts')
    op.drop_index(op.f('ix_accounts_external_id'), table_name='accounts')
    op.drop_table('accounts')

    # Drop party columns/indexes
    op.drop_index(op.f('ix_parties_batch_id'), table_name='parties')
    op.drop_index(op.f('ix_parties_external_id'), table_name='parties')
    op.drop_column('parties', 'batch_id')
    op.drop_column('parties', 'external_id')
