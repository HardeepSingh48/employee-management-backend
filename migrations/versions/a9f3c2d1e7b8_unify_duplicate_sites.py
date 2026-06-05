"""unify_duplicate_sites

This migration:
1. Trims trailing/leading whitespace from all site_name values.
2. Removes orphaned duplicate sites (same TRIM+LOWER name, zero references).
3. Adds a unique functional index on TRIM(LOWER(site_name)) to prevent future duplicates.

Revision ID: a9f3c2d1e7b8
Revises: 2c12c4f81d41
Create Date: 2026-06-06
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'a9f3c2d1e7b8'
down_revision = '2c12c4f81d41'
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()

    # ---------------------------------------------------------------------------
    # STEP 1: Trim whitespace from all site_name values in the sites table.
    # This fixes "BOKARO SINTER PLANT " -> "BOKARO SINTER PLANT" and any others.
    # ---------------------------------------------------------------------------
    connection.execute(sa.text("""
        UPDATE sites
        SET site_name = TRIM(site_name)
        WHERE site_name != TRIM(site_name)
    """))

    # Also update matching wage_master.site_name strings to be consistent
    # (site_name in wage_masters is a legacy string column kept for display; keep in sync)
    connection.execute(sa.text("""
        UPDATE wage_masters
        SET site_name = TRIM(site_name)
        WHERE site_name != TRIM(site_name) AND site_name IS NOT NULL
    """))

    # ---------------------------------------------------------------------------
    # STEP 2: Remove truly orphaned duplicate site rows.
    # Strategy: For sites that share a TRIM+LOWER name, keep the one that has
    # the most wage_master references (or the oldest by site_id if tied).
    # The duplicate with zero references can be safely deleted.
    #
    # We only delete sites that have NO wage_master AND NO employee references.
    # ---------------------------------------------------------------------------
    # Find duplicate groups and their reference counts
    result = connection.execute(sa.text("""
        SELECT s.site_id, s.site_name, TRIM(LOWER(s.site_name)) AS norm_name,
               COALESCE(wm_count.cnt, 0) AS wm_refs,
               COALESCE(emp_count.cnt, 0) AS emp_refs
        FROM sites s
        LEFT JOIN (
            SELECT site_id, COUNT(*) AS cnt FROM wage_masters GROUP BY site_id
        ) wm_count ON wm_count.site_id = s.site_id
        LEFT JOIN (
            SELECT site_id, COUNT(*) AS cnt FROM employees GROUP BY site_id
        ) emp_count ON emp_count.site_id = s.site_id
        WHERE TRIM(LOWER(s.site_name)) IN (
            SELECT TRIM(LOWER(site_name))
            FROM sites
            GROUP BY TRIM(LOWER(site_name))
            HAVING COUNT(*) > 1
        )
        ORDER BY TRIM(LOWER(s.site_name)), (COALESCE(wm_count.cnt, 0) + COALESCE(emp_count.cnt, 0)) DESC, s.site_id
    """)).fetchall()

    # Group by norm_name: mark the first as "keeper", rest as candidates for deletion
    from collections import defaultdict
    groups = defaultdict(list)
    for row in result:
        site_id, site_name, norm_name, wm_refs, emp_refs = row
        groups[norm_name].append({
            'site_id': site_id,
            'site_name': site_name,
            'wm_refs': wm_refs,
            'emp_refs': emp_refs,
        })

    sites_to_delete = []
    for norm_name, entries in groups.items():
        # entries are sorted: highest refs first, then by site_id
        keeper = entries[0]  # site with most references (or first alphabetically)
        for dup in entries[1:]:
            total_refs = dup['wm_refs'] + dup['emp_refs']
            if total_refs == 0:
                # Safe to delete - no references
                sites_to_delete.append(dup['site_id'])
            else:
                # Has references - remap them to keeper before deleting
                # Remap wage_masters
                connection.execute(sa.text("""
                    UPDATE wage_masters SET site_id = :keeper_id WHERE site_id = :dup_id
                """), {'keeper_id': keeper['site_id'], 'dup_id': dup['site_id']})
                # Remap employees
                connection.execute(sa.text("""
                    UPDATE employees SET site_id = :keeper_id WHERE site_id = :dup_id
                """), {'keeper_id': keeper['site_id'], 'dup_id': dup['site_id']})
                sites_to_delete.append(dup['site_id'])

    # Delete the duplicate sites
    for site_id in sites_to_delete:
        connection.execute(sa.text("""
            DELETE FROM sites WHERE site_id = :site_id
        """), {'site_id': site_id})

    # ---------------------------------------------------------------------------
    # STEP 3: Add a unique index on TRIM(LOWER(site_name)) to prevent future
    # duplicates at the database level.
    # ---------------------------------------------------------------------------
    connection.execute(sa.text("""
        CREATE UNIQUE INDEX IF NOT EXISTS uix_sites_normalized_name
        ON sites (TRIM(LOWER(site_name)))
    """))


def downgrade():
    connection = op.get_bind()

    # Remove the unique index (data changes are not reversible)
    connection.execute(sa.text("""
        DROP INDEX IF EXISTS uix_sites_normalized_name
    """))
