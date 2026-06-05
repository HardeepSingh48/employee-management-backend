"""add_wagemaster_site_id

Revision ID: 20260602_add_wagemaster_site_id
Revises: 
Create Date: 2026-06-02 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20260602_add_wagemaster_site_id'
down_revision = 'aeb3bb3f1bbe'
branch_labels = None
depends_on = None


def upgrade():
    # Add nullable site_id column to wage_masters
    op.add_column('wage_masters', sa.Column('site_id', sa.String(length=50), nullable=True))
    
    # Data migration: populate site_id based on trimmed/case-insensitive site_name match
    connection = op.get_bind()
    connection.execute(sa.text("""
        UPDATE wage_masters
        SET site_id = sites.site_id
        FROM sites
        WHERE TRIM(LOWER(wage_masters.site_name)) = TRIM(LOWER(sites.site_name))
    """))
    
    # Optionally create index
    op.create_index('ix_wage_masters_site_id', 'wage_masters', ['site_id'])


def downgrade():
    op.drop_index('ix_wage_masters_site_id', table_name='wage_masters')
    op.drop_column('wage_masters', 'site_id')

