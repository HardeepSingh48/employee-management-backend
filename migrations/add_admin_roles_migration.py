"""
Database Migration: Add admin1 and admin2 roles
Migration Strategy: Option B - Convert existing 'admin' users to 'admin2' (restricted)

This migration:
1. Drops the existing CHECK constraint on users.role
2. Adds new CHECK constraint including 'admin1' and 'admin2'
3. Converts all existing 'admin' users to 'admin2' (restricted access)
4. Keeps 'admin' in constraint for backward compatibility

IMPORTANT: Backup database before running this migration!

Run with: python migrations/add_admin_roles_migration.py
"""

import sys
import os

# Add parent directory to path to allow imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from models import db
from sqlalchemy import text

def upgrade():
    """Apply the migration"""
    try:
        print("Starting migration: Add admin1 and admin2 roles...")
        
        # Step 1: Drop existing CHECK constraint
        print("Step 1: Dropping existing CHECK constraint on users.role...")
        db.session.execute(text("""
            ALTER TABLE users DROP CONSTRAINT IF EXISTS users_role_check;
        """))
        db.session.commit()
        print("✓ Constraint dropped")
        
        # Step 2: Add new CHECK constraint with admin1 and admin2
        print("Step 2: Adding new CHECK constraint with admin1, admin2...")
        db.session.execute(text("""
            ALTER TABLE users 
            ADD CONSTRAINT users_role_check 
            CHECK (role IN ('superadmin', 'admin', 'admin1', 'admin2', 'hr', 'manager', 'supervisor', 'employee'));
        """))
        db.session.commit()
        print("✓ New constraint added")
        
        # Step 3: Migrate existing 'admin' users to 'admin2' (Option B)
        print("Step 3: Migrating existing 'admin' users to 'admin2'...")
        
        # First, count how many admins will be affected
        result = db.session.execute(text("SELECT COUNT(*) FROM users WHERE role = 'admin'"))
        admin_count = result.scalar()
        print(f"Found {admin_count} admin user(s) to migrate...")
        
        if admin_count > 0:
            # Perform the migration
            db.session.execute(text("""
                UPDATE users 
                SET role = 'admin2', 
                    updated_date = NOW(),
                    updated_by = 'system_migration'
                WHERE role = 'admin';
            """))
            db.session.commit()
            print(f"✓ Successfully migrated {admin_count} admin user(s) to admin2")
            print("⚠️  NOTE: These users now have RESTRICTED access (cannot modify salary codes)")
            print("⚠️  To grant full access, manually update specific users to 'admin1'")
        else:
            print("No admin users found to migrate")
        
        print("\n✅ Migration completed successfully!")
        print("\nNext steps:")
        print("1. Manually promote users who need salary code access to 'admin1':")
        print("   UPDATE users SET role = 'admin1' WHERE email = 'user@example.com';")
        print("2. Deploy updated backend code with new role logic")
        print("3. Update frontend to support new roles")
        
    except Exception as e:
        print(f"\n❌ Migration failed: {str(e)}")
        db.session.rollback()
        sys.exit(1)

def downgrade():
    """Revert the migration"""
    try:
        print("Starting rollback: Reverting admin1/admin2 to admin...")
        
        # Count affected users
        result = db.session.execute(text("""
            SELECT COUNT(*) FROM users WHERE role IN ('admin1', 'admin2')
        """))
        count = result.scalar()
        print(f"Found {count} user(s) with admin1/admin2 roles...")
        
        # Revert admin1 and admin2 back to admin
        print("Reverting admin1/admin2 users to 'admin'...")
        db.session.execute(text("""
            UPDATE users 
            SET role = 'admin',
                updated_date = NOW(),
                updated_by = 'system_rollback'
            WHERE role IN ('admin1', 'admin2');
        """))
        db.session.commit()
        print(f"✓ Reverted {count} user(s) to 'admin'")
        
        # Drop new constraint
        print("Dropping new CHECK constraint...")
        db.session.execute(text("""
            ALTER TABLE users DROP CONSTRAINT IF EXISTS users_role_check;
        """))
        db.session.commit()
        
        # Restore original constraint
        print("Restoring original CHECK constraint...")
        db.session.execute(text("""
            ALTER TABLE users 
            ADD CONSTRAINT users_role_check 
            CHECK (role IN ('admin', 'superadmin', 'hr', 'manager', 'supervisor', 'employee'));
        """))
        db.session.commit()
        
        print("\n✅ Rollback completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Rollback failed: {str(e)}")
        db.session.rollback()
        sys.exit(1)

if __name__ == "__main__":
    from app import app
    
    with app.app_context():
        print("\n" + "="*60)
        print("DATABASE MIGRATION: Add Admin1 and Admin2 Roles")
        print("="*60 + "\n")
        
        print("⚠️  WARNING: This will modify your database!")
        print("⚠️  Ensure you have a backup before proceeding!\n")
        
        choice = input("Do you want to:\n1. Apply migration (upgrade)\n2. Rollback migration (downgrade)\n3. Cancel\n\nEnter choice (1/2/3): ")
        
        if choice == "1":
            print("\n" + "-"*60)
            upgrade()
            print("-"*60 + "\n")
        elif choice == "2":
            print("\n" + "-"*60)
            downgrade()
            print("-"*60 + "\n")
        else:
            print("Migration cancelled.")
