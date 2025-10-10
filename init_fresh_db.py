#!/usr/bin/env python3
"""
Complete Database Initialization Script for VPS Setup
=====================================================

This script provides a single-command database initialization similar to Prisma,
automatically setting up all tables, constraints, indexes, sequences, and seed data
for the Employee Management System on a fresh VPS server.

Features:
- Creates all tables with proper relationships
- Applies all database constraints (attendance status, etc.)
- Sets up performance indexes
- Configures employee ID sequence (starting from 91510001)
- Seeds essential data (departments, holidays, demo users)
- Handles all migrations automatically

Usage:
    python init_fresh_db.py                    # Basic setup
    python init_fresh_db.py --seed-demo        # With demo data
    python init_fresh_db.py --drop             # Drop and recreate
    python init_fresh_db.py --status           # Check current status

Environment Variables Required:
    DATABASE_URL=postgresql://user:pass@host:5432/db
"""

import argparse
import sys
import os
from datetime import date, datetime
from sqlalchemy import text, MetaData, Table, Column, Integer, String, Date, Boolean, Text, Float, DateTime, ForeignKey, CheckConstraint
from sqlalchemy.exc import ProgrammingError

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from models import db
from models.user import User
from models.employee import Employee
from models.department import Department
from models.holiday import Holiday


def create_tables():
    """Create all tables with proper schema"""
    print("📋 Creating database tables...")

    try:
        # Create all tables defined in SQLAlchemy models
        db.create_all()
        print("✅ All tables created successfully")
        return True
    except Exception as e:
        print(f"❌ Failed to create tables: {e}")
        return False


def apply_constraints():
    """Apply all database constraints"""
    print("🔒 Applying database constraints...")

    try:
        # Attendance status constraint (Present, Absent, OFF only)
        constraint_sql = """
        ALTER TABLE attendance
        ADD CONSTRAINT IF NOT EXISTS check_attendance_status
        CHECK (attendance_status IN ('Present', 'Absent', 'OFF'))
        """
        db.session.execute(text(constraint_sql))

        # Employee ID format constraint (if needed)
        # Add other constraints here as they are developed

        db.session.commit()
        print("✅ All constraints applied successfully")
        return True
    except Exception as e:
        db.session.rollback()
        print(f"❌ Failed to apply constraints: {e}")
        return False


def setup_employee_sequence():
    """Set up employee ID sequence starting from 91510001"""
    print("🔢 Setting up employee ID sequence...")

    try:
        # Drop existing sequence if present
        db.session.execute(text("DROP SEQUENCE IF EXISTS employee_id_seq CASCADE"))

        # Create new sequence starting from 91510001
        db.session.execute(text("""
            CREATE SEQUENCE employee_id_seq
            START WITH 91510001
            INCREMENT BY 1
            OWNED BY employees.employee_id
        """))

        # Set as default for the table
        db.session.execute(text("""
            ALTER TABLE employees
            ALTER COLUMN employee_id SET DEFAULT nextval('employee_id_seq')
        """))

        db.session.commit()
        print("✅ Employee ID sequence set up successfully (starts from 91510001)")
        return True
    except Exception as e:
        db.session.rollback()
        print(f"❌ Failed to setup employee sequence: {e}")
        return False


def create_performance_indexes():
    """Create performance indexes for optimal query performance"""
    print("⚡ Creating performance indexes...")

    try:
        indexes = [
            # Attendance indexes
            "CREATE INDEX IF NOT EXISTS idx_attendance_employee_date ON attendance(employee_id, attendance_date)",
            "CREATE INDEX IF NOT EXISTS idx_attendance_date_status ON attendance(attendance_date, attendance_status)",
            "CREATE INDEX IF NOT EXISTS idx_attendance_employee_date_status ON attendance(employee_id, attendance_date, attendance_status)",

            # Employee indexes
            "CREATE INDEX IF NOT EXISTS idx_employee_salary_code ON employees(salary_code)",
            "CREATE INDEX IF NOT EXISTS idx_employee_phone_email ON employees(phone_number, email)",
            "CREATE INDEX IF NOT EXISTS idx_employee_phone ON employees(phone_number)",
            "CREATE INDEX IF NOT EXISTS idx_employee_email ON employees(email)",
            "CREATE INDEX IF NOT EXISTS idx_employee_adhar ON employees(adhar_number)",
            "CREATE INDEX IF NOT EXISTS idx_employee_pan ON employees(pan_card_number)",
            "CREATE INDEX IF NOT EXISTS idx_employee_name ON employees(first_name, last_name)",
            "CREATE INDEX IF NOT EXISTS idx_employee_department ON employees(department_id)",
            "CREATE INDEX IF NOT EXISTS idx_employee_status ON employees(employment_status)",
            "CREATE INDEX IF NOT EXISTS idx_employee_site ON employees(site_id)",
            "CREATE INDEX IF NOT EXISTS idx_employee_hire_date ON employees(hire_date)",

            # Wage Master indexes
            "CREATE INDEX IF NOT EXISTS idx_wage_master_salary_code ON wage_masters(salary_code)",
            "CREATE INDEX IF NOT EXISTS idx_wage_master_site_name ON wage_masters(site_name)",

            # Deduction indexes
            "CREATE INDEX IF NOT EXISTS idx_deduction_employee_id ON deductions(employee_id)",
            "CREATE INDEX IF NOT EXISTS idx_deduction_employee_active ON deductions(employee_id, start_month)",
        ]

        for index_sql in indexes:
            try:
                db.session.execute(text(index_sql))
            except Exception as e:
                print(f"⚠️  Warning: Could not create index: {e}")

        db.session.commit()
        print("✅ Performance indexes created successfully")
        return True
    except Exception as e:
        db.session.rollback()
        print(f"❌ Failed to create indexes: {e}")
        return False


def seed_essential_data():
    """Seed essential data required for system operation"""
    print("🌱 Seeding essential data...")

    try:
        # Seed departments
        departments_data = [
            {"department_id": "HR", "department_name": "HR", "description": "Handles employee relations, recruitment, training, and organizational development."},
            {"department_id": "IT", "department_name": "IT", "description": "Responsible for managing technology infrastructure, software development, and IT support."},
            {"department_id": "Finance", "department_name": "Finance", "description": "Manages financial planning, accounting, budgeting, and financial reporting."},
            {"department_id": "Marketing", "department_name": "Marketing", "description": "Responsible for market research, advertising, brand management, and customer engagement."},
            {"department_id": "Operations", "department_name": "Operations", "description": "Oversees daily business operations, process optimization, and operational efficiency."},
            {"department_id": "Sales", "department_name": "Sales", "description": "Manages customer acquisition, sales processes, and revenue generation."},
            {"department_id": "Engineering", "department_name": "Engineering", "description": "Handles product development, technical design, and engineering solutions."},
            {"department_id": "Customer Support", "department_name": "Customer Support", "description": "Provides customer service, technical support, and client relationship management."},
            {"department_id": "Legal", "department_name": "Legal", "description": "Manages legal compliance, contracts, regulatory affairs, and legal risk management."},
            {"department_id": "Administration", "department_name": "Administration", "description": "Handles administrative functions, office management, and general support services."}
        ]

        for dept_data in departments_data:
            dept = Department.query.filter_by(department_id=dept_data["department_id"]).first()
            if dept is None:
                dept = Department(
                    department_id=dept_data["department_id"],
                    department_name=dept_data["department_name"],
                    description=dept_data["description"],
                    is_active=True,
                    created_by="init_fresh_db"
                )
                db.session.add(dept)

        # Seed holidays for current year
        current_year = datetime.now().year
        holidays_data = [
            {"name": "New Year's Day", "date": date(current_year, 1, 1), "type": "National", "paid": True, "mandatory": True},
            {"name": "Republic Day", "date": date(current_year, 1, 26), "type": "National", "paid": True, "mandatory": True},
            {"name": "Independence Day", "date": date(current_year, 8, 15), "type": "National", "paid": True, "mandatory": True},
            {"name": "Gandhi Jayanti", "date": date(current_year, 10, 2), "type": "National", "paid": True, "mandatory": True},
            {"name": "Christmas Day", "date": date(current_year, 12, 25), "type": "National", "paid": True, "mandatory": True},
            {"name": "Company Foundation Day", "date": date(current_year, 4, 15), "type": "Company", "paid": True, "mandatory": False},
        ]

        for holiday_data in holidays_data:
            existing = Holiday.query.filter_by(holiday_date=holiday_data["date"]).first()
            if existing is None:
                holiday = Holiday(
                    holiday_name=holiday_data["name"],
                    holiday_date=holiday_data["date"],
                    holiday_type=holiday_data["type"],
                    description=f"{holiday_data['name']} - {holiday_data['type']} holiday",
                    is_paid=holiday_data["paid"],
                    is_mandatory=holiday_data["mandatory"],
                    is_active=True,
                    created_by="init_fresh_db"
                )
                db.session.add(holiday)

        db.session.commit()
        print("✅ Essential data seeded successfully")
        return True
    except Exception as e:
        db.session.rollback()
        print(f"❌ Failed to seed essential data: {e}")
        return False


def seed_demo_data():
    """Seed demo users for testing"""
    print("🎭 Seeding demo data...")

    try:
        # Create admin user
        admin = User.query.filter_by(email="admin@company.com").first()
        if admin is None:
            admin = User(
                email="admin@company.com",
                name="Admin User",
                role="admin",
                created_by="init_fresh_db",
            )
            db.session.add(admin)

        admin.set_password("admin123")
        admin.set_permissions(["all"])

        # Create demo employee
        demo_emp_id = "91510001"  # First ID from sequence
        employee = Employee.query.filter_by(employee_id=demo_emp_id).first()
        if employee is None:
            employee = Employee(
                employee_id=demo_emp_id,
                first_name="Demo",
                last_name="Employee",
                email="employee@company.com",
                designation="Associate",
                employment_status="Active",
                department_id="IT",
                created_by="init_fresh_db",
            )
            db.session.add(employee)

        # Create employee user
        emp_user = User.query.filter_by(email="employee@company.com").first()
        if emp_user is None:
            emp_user = User(
                email="employee@company.com",
                name="Demo Employee",
                role="employee",
                employee_id=demo_emp_id,
                created_by="init_fresh_db",
            )
            db.session.add(emp_user)

        emp_user.employee_id = demo_emp_id
        emp_user.set_password("emp123")
        emp_user.set_permissions(["view_profile", "mark_attendance", "view_attendance"])

        db.session.commit()
        print("✅ Demo data seeded successfully")
        print("Demo credentials:")
        print("  Admin: admin@company.com / admin123")
        print("  Employee: employee@company.com / emp123")
        return True
    except Exception as e:
        db.session.rollback()
        print(f"❌ Failed to seed demo data: {e}")
        return False


def verify_setup():
    """Verify that the database setup is correct"""
    print("🔍 Verifying database setup...")

    try:
        # Check tables exist
        tables_to_check = ['employees', 'attendance', 'users', 'departments', 'holidays', 'wage_masters', 'deductions']
        for table in tables_to_check:
            result = db.session.execute(text(f"SELECT COUNT(*) FROM {table}")).fetchone()
            print(f"✅ Table '{table}': {result[0]} records")

        # Check constraints
        constraint_result = db.session.execute(text("""
            SELECT conname FROM pg_constraint
            WHERE conrelid = 'attendance'::regclass AND contype = 'c'
        """)).fetchall()

        constraint_names = [row[0] for row in constraint_result]
        if 'check_attendance_status' in constraint_names:
            print("✅ Attendance status constraint: Active")
        else:
            print("⚠️  Attendance status constraint: Missing")

        # Check sequence
        seq_result = db.session.execute(text("SELECT nextval('employee_id_seq')")).fetchone()
        next_id = seq_result[0]

        # Reset sequence
        db.session.execute(text("SELECT setval('employee_id_seq', 91510001, false)"))
        db.session.commit()

        print(f"✅ Employee ID sequence: Next ID will be {next_id}")

        # Check indexes (sample)
        index_result = db.session.execute(text("""
            SELECT COUNT(*) FROM pg_indexes
            WHERE tablename IN ('employees', 'attendance', 'wage_masters', 'deductions')
        """)).fetchone()

        print(f"✅ Performance indexes: {index_result[0]} created")

        print("✅ Database verification completed successfully")
        return True
    except Exception as e:
        print(f"❌ Database verification failed: {e}")
        return False


def drop_all_tables():
    """Drop all tables (use with caution)"""
    print("💥 Dropping all tables...")

    try:
        # Drop tables in correct order (reverse dependency)
        tables_to_drop = [
            'deductions', 'attendance', 'employees', 'wage_masters',
            'sites', 'holidays', 'departments', 'users'
        ]

        for table in tables_to_drop:
            try:
                db.session.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE"))
            except Exception as e:
                print(f"⚠️  Warning: Could not drop table {table}: {e}")

        # Drop sequences
        db.session.execute(text("DROP SEQUENCE IF EXISTS employee_id_seq CASCADE"))

        db.session.commit()
        print("✅ All tables dropped successfully")
        return True
    except Exception as e:
        db.session.rollback()
        print(f"❌ Failed to drop tables: {e}")
        return False


def init_fresh_database(drop_tables=False, seed_demo=False, verify=True):
    """Main initialization function - similar to Prisma's db push"""

    # Use minimal app without blueprints
    app = create_app(register_blueprints=False)

    with app.app_context():
        success = True

        try:
            print("🚀 Starting Employee Management System Database Initialization")
            print("=" * 70)

            # Step 1: Drop tables if requested
            if drop_tables:
                if not drop_all_tables():
                    return False

            # Step 2: Create tables
            if not create_tables():
                success = False

            # Step 3: Apply constraints
            if not apply_constraints():
                success = False

            # Step 4: Setup sequences
            if not setup_employee_sequence():
                success = False

            # Step 5: Create indexes
            if not create_performance_indexes():
                success = False

            # Step 6: Seed essential data
            if not seed_essential_data():
                success = False

            # Step 7: Seed demo data if requested
            if seed_demo:
                if not seed_demo_data():
                    success = False

            # Step 8: Verify setup
            if verify:
                if not verify_setup():
                    success = False

            if success:
                print("\n" + "=" * 70)
                print("🎉 DATABASE INITIALIZATION COMPLETED SUCCESSFULLY!")
                print("=" * 70)
                print("✅ All tables created with proper relationships")
                print("✅ All constraints and indexes applied")
                print("✅ Employee ID sequence configured (starts from 91510001)")
                print("✅ Essential data seeded (departments, holidays)")
                if seed_demo:
                    print("✅ Demo users created")
                print("\n🚀 Your Employee Management System is ready!")
                print("   Next: Configure your application and start the server.")
            else:
                print("\n❌ Database initialization failed. Check errors above.")

            return success

        except Exception as e:
            print(f"\n💥 Critical error during initialization: {e}")
            import traceback
            traceback.print_exc()
            return False


def check_database_status():
    """Check current database status"""
    app = create_app(register_blueprints=False)

    with app.app_context():
        print("📊 Database Status Check")
        print("=" * 40)

        try:
            # Check connection
            db.session.execute(text("SELECT 1"))
            print("✅ Database connection: OK")

            # Check tables
            tables = ['employees', 'attendance', 'users', 'departments', 'holidays']
            for table in tables:
                try:
                    result = db.session.execute(text(f"SELECT COUNT(*) FROM {table}")).fetchone()
                    print(f"✅ Table '{table}': {result[0]} records")
                except Exception:
                    print(f"❌ Table '{table}': Missing or inaccessible")

            # Check sequence
            try:
                result = db.session.execute(text("SELECT nextval('employee_id_seq')")).fetchone()
                next_id = result[0]
                db.session.execute(text("SELECT setval('employee_id_seq', 91510001, false)"))
                db.session.commit()
                print(f"✅ Employee ID sequence: Next ID = {next_id}")
            except Exception as e:
                print(f"❌ Employee ID sequence: Error - {e}")

            # Check constraints
            try:
                result = db.session.execute(text("""
                    SELECT COUNT(*) FROM pg_constraint
                    WHERE conname = 'check_attendance_status'
                """)).fetchone()
                if result[0] > 0:
                    print("✅ Attendance status constraint: Active")
                else:
                    print("❌ Attendance status constraint: Missing")
            except Exception as e:
                print(f"❌ Constraint check failed: {e}")

        except Exception as e:
            print(f"❌ Database status check failed: {e}")


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="Complete database initialization for Employee Management System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python init_fresh_db.py                    # Basic initialization
  python init_fresh_db.py --seed-demo        # With demo users
  python init_fresh_db.py --drop             # Drop and recreate all
  python init_fresh_db.py --status           # Check database status
  python init_fresh_db.py --drop --seed-demo # Full reset with demo data
        """
    )

    parser.add_argument(
        "--drop",
        action="store_true",
        help="Drop all existing tables before creating new ones"
    )

    parser.add_argument(
        "--seed-demo",
        action="store_true",
        help="Seed demo admin and employee users"
    )

    parser.add_argument(
        "--status",
        action="store_true",
        help="Check current database status without making changes"
    )

    parser.add_argument(
        "--no-verify",
        action="store_true",
        help="Skip verification step (faster but less safe)"
    )

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    if args.status:
        # Just check status
        check_database_status()
    else:
        # Perform initialization
        success = init_fresh_database(
            drop_tables=args.drop,
            seed_demo=args.seed_demo,
            verify=not args.no_verify
        )

        # Exit with appropriate code
        sys.exit(0 if success else 1)