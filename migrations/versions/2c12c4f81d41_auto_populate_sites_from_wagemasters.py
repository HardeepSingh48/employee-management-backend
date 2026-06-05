"""auto_populate_sites_from_wagemasters

Revision ID: 2c12c4f81d41
Revises: 20260602_add_wagemaster_site_id
Create Date: 2026-06-05 23:31:17.552471

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2c12c4f81d41'
down_revision = '20260602_add_wagemaster_site_id'
branch_labels = None
depends_on = None


def upgrade():
    # Use connection to execute queries and update database
    connection = op.get_bind()
    
    # 1. Select all distinct site_name and state from wage_masters that do not have a matching site in the sites table
    # We do case-insensitive, trimmed comparison to check if it exists in the sites table
    result = connection.execute(sa.text("""
        SELECT DISTINCT wm.site_name, wm.state
        FROM wage_masters wm
        LEFT JOIN sites s ON TRIM(LOWER(wm.site_name)) = TRIM(LOWER(s.site_name))
        WHERE s.site_id IS NULL AND wm.site_name IS NOT NULL AND wm.site_name != ''
    """)).fetchall()
    
    # For each unmatched site, generate a new site_id and insert it into sites table
    import uuid
    from datetime import date
    
    for row in result:
        site_name = row[0].strip()
        state = row[1].strip() if row[1] else "Unknown"
        site_id = f"SITE-{uuid.uuid4().hex[:8].upper()}"
        
        # Insert new site
        connection.execute(
            sa.text("""
                INSERT INTO sites (site_id, site_name, location, state, is_active, created_date, created_by)
                VALUES (:site_id, :site_name, NULL, :state, TRUE, :created_date, 'migration')
            """),
            {
                "site_id": site_id,
                "site_name": site_name,
                "state": state,
                "created_date": date.today()
            }
        )
        
    # 2. Update wage_masters set site_id from sites where it's currently NULL and matches the site_name
    connection.execute(sa.text("""
        UPDATE wage_masters
        SET site_id = sites.site_id
        FROM sites
        WHERE wage_masters.site_id IS NULL
          AND TRIM(LOWER(wage_masters.site_name)) = TRIM(LOWER(sites.site_name))
    """))


def downgrade():
    connection = op.get_bind()
    
    # Set site_id = NULL in wage_masters for sites created by this migration
    connection.execute(sa.text("""
        UPDATE wage_masters
        SET site_id = NULL
        FROM sites
        WHERE wage_masters.site_id = sites.site_id
          AND sites.created_by = 'migration'
    """))
    
    # Delete sites created by this migration
    connection.execute(sa.text("""
        DELETE FROM sites
        WHERE created_by = 'migration'
    """))

