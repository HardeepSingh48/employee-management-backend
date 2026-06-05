"""merge_nospace_duplicate_sites

Merges sites that are identical after removing spaces (same physical site,
different typing conventions). Keeps the 'with spaces' version as canonical.

Pairs merged:
  - BOKAROSINTERPLANT  -> BOKARO SINTER PLANT  (both JH)
  - PATNAPC08          -> PATNA PC08           (both BR)

Revision ID: b1e4f7a2c9d3
Revises: a9f3c2d1e7b8
Create Date: 2026-06-06
"""
from alembic import op
import sqlalchemy as sa
from collections import defaultdict

revision = 'b1e4f7a2c9d3'
down_revision = 'a9f3c2d1e7b8'
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()

    # -----------------------------------------------------------------------
    # Find all site pairs that match after removing spaces (but are not already
    # exact TRIM+LOWER duplicates — those were handled in the previous migration).
    # Keep the one with MORE wage_master references, or the one WITH spaces if tied.
    # -----------------------------------------------------------------------
    result = connection.execute(sa.text("""
        SELECT
            a.site_id AS id_a, a.site_name AS name_a, a.state AS state_a,
            b.site_id AS id_b, b.site_name AS name_b, b.state AS state_b,
            COALESCE(wm_a.cnt, 0) AS wm_a,
            COALESCE(wm_b.cnt, 0) AS wm_b,
            COALESCE(emp_a.cnt, 0) AS emp_a,
            COALESCE(emp_b.cnt, 0) AS emp_b
        FROM sites a
        JOIN sites b
            ON a.site_id < b.site_id
            AND LOWER(REPLACE(TRIM(a.site_name), ' ', '')) = LOWER(REPLACE(TRIM(b.site_name), ' ', ''))
            AND TRIM(LOWER(a.site_name)) != TRIM(LOWER(b.site_name))
        LEFT JOIN (SELECT site_id, COUNT(*) cnt FROM wage_masters GROUP BY site_id) wm_a ON wm_a.site_id = a.site_id
        LEFT JOIN (SELECT site_id, COUNT(*) cnt FROM wage_masters GROUP BY site_id) wm_b ON wm_b.site_id = b.site_id
        LEFT JOIN (SELECT site_id, COUNT(*) cnt FROM employees    GROUP BY site_id) emp_a ON emp_a.site_id = a.site_id
        LEFT JOIN (SELECT site_id, COUNT(*) cnt FROM employees    GROUP BY site_id) emp_b ON emp_b.site_id = b.site_id
        ORDER BY LOWER(REPLACE(TRIM(a.site_name), ' ', ''))
    """)).fetchall()

    for row in result:
        id_a, name_a, state_a, id_b, name_b, state_b, wm_a, wm_b, emp_a, emp_b = row

        # Determine keeper: prefer site with spaces (more readable), but also
        # prefer higher reference count to minimise remapping.
        # We identify which name has spaces in it.
        a_has_spaces = ' ' in name_a.strip()
        b_has_spaces = ' ' in name_b.strip()

        refs_a = wm_a + emp_a
        refs_b = wm_b + emp_b

        # Prefer: (1) has spaces, (2) more refs, (3) alphabetically first id
        if a_has_spaces and not b_has_spaces:
            keeper_id, keeper_name = id_a, name_a
            dup_id, dup_name = id_b, name_b
        elif b_has_spaces and not a_has_spaces:
            keeper_id, keeper_name = id_b, name_b
            dup_id, dup_name = id_a, name_a
        elif refs_a >= refs_b:
            keeper_id, keeper_name = id_a, name_a
            dup_id, dup_name = id_b, name_b
        else:
            keeper_id, keeper_name = id_b, name_b
            dup_id, dup_name = id_a, name_a

        # Remap wage_masters from dup to keeper
        connection.execute(sa.text("""
            UPDATE wage_masters SET site_id = :keeper WHERE site_id = :dup
        """), {'keeper': keeper_id, 'dup': dup_id})

        # Also update site_name string in wage_masters to match keeper for consistency
        connection.execute(sa.text("""
            UPDATE wage_masters SET site_name = :keeper_name WHERE site_id = :keeper
        """), {'keeper_name': keeper_name.strip(), 'keeper': keeper_id})

        # Remap employees from dup to keeper
        connection.execute(sa.text("""
            UPDATE employees SET site_id = :keeper WHERE site_id = :dup
        """), {'keeper': keeper_id, 'dup': dup_id})

        # Delete the duplicate site
        connection.execute(sa.text("""
            DELETE FROM sites WHERE site_id = :dup
        """), {'dup': dup_id})


def downgrade():
    # Data merges are not reversible — the unique index remains.
    pass
