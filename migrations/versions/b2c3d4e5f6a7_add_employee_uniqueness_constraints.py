"""Add partial uniqueness constraints on adhar_number and phone_number for active employees

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-04-02 00:49:00.000000

This migration:
  1. PRE-CHECK: Reports any existing duplicate Aadhaar/phone pairs.
     If duplicates are found, the migration raises an error and does NOT apply
     the unique constraints. Fix the duplicates manually first, then re-run.
  2. Creates PostgreSQL partial unique indexes (only among non-deleted employees):
       idx_unique_active_adhar  ON employees(adhar_number) WHERE is_deleted = FALSE
       idx_unique_active_phone  ON employees(phone_number) WHERE is_deleted = FALSE
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision = 'b2c3d4e5f6a7'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()

    # ---------------------------------------------------------------
    # PRE-CHECK: Detect duplicate Aadhaar numbers among active employees
    # ---------------------------------------------------------------
    adhar_dupes = conn.execute(text("""
        SELECT adhar_number, COUNT(*) as cnt, array_agg(employee_id) as ids
        FROM employees
        WHERE is_deleted = FALSE
          AND adhar_number IS NOT NULL
          AND adhar_number != ''
          AND adhar_number != '000000000000'
        GROUP BY adhar_number
        HAVING COUNT(*) > 1
    """)).fetchall()

    if adhar_dupes:
        conflict_info = "\n".join(
            f"  Aadhaar '{row[0]}' shared by employee IDs: {row[2]}"
            for row in adhar_dupes
        )
        raise Exception(
            f"\n\n[MIGRATION BLOCKED] Found {len(adhar_dupes)} duplicate Aadhaar number(s) "
            f"among active employees. Resolve these conflicts manually before re-running:\n"
            f"{conflict_info}\n"
        )

    # ---------------------------------------------------------------
    # PRE-CHECK: Detect duplicate phone numbers among active employees
    # ---------------------------------------------------------------
    phone_dupes = conn.execute(text("""
        SELECT phone_number, COUNT(*) as cnt, array_agg(employee_id) as ids
        FROM employees
        WHERE is_deleted = FALSE
          AND phone_number IS NOT NULL
          AND phone_number != ''
          AND phone_number != '9999999999'
        GROUP BY phone_number
        HAVING COUNT(*) > 1
    """)).fetchall()

    if phone_dupes:
        conflict_info = "\n".join(
            f"  Phone '{row[0]}' shared by employee IDs: {row[2]}"
            for row in phone_dupes
        )
        raise Exception(
            f"\n\n[MIGRATION BLOCKED] Found {len(phone_dupes)} duplicate phone number(s) "
            f"among active employees. Resolve these conflicts manually before re-running:\n"
            f"{conflict_info}\n"
        )

    # ---------------------------------------------------------------
    # CREATE partial unique indexes (PostgreSQL only)
    # Note: We exclude placeholder values ('000000000000', '9999999999')
    #       that bulk-upload uses as defaults.
    # ---------------------------------------------------------------
    conn.execute(text("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_active_adhar
        ON employees(adhar_number)
        WHERE is_deleted = FALSE
          AND adhar_number IS NOT NULL
          AND adhar_number != ''
          AND adhar_number != '000000000000'
    """))

    conn.execute(text("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_active_phone
        ON employees(phone_number)
        WHERE is_deleted = FALSE
          AND phone_number IS NOT NULL
          AND phone_number != ''
          AND phone_number != '9999999999'
    """))


def downgrade():
    conn = op.get_bind()
    conn.execute(text("DROP INDEX IF EXISTS idx_unique_active_adhar"))
    conn.execute(text("DROP INDEX IF EXISTS idx_unique_active_phone"))
