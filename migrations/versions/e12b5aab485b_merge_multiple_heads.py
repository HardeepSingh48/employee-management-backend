"""merge multiple heads

Revision ID: e12b5aab485b
Revises: 20260622_add_employee_geo_checkin_fields, c2f5e8b3a1d6
Create Date: 2026-06-24 01:14:34.037620

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e12b5aab485b'
down_revision = ('add_employee_geo_fields', 'c2f5e8b3a1d6')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
