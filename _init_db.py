#!/usr/bin/env python3
"""
Initialize the database (create tables) and optionally seed demo users.

Usage examples (Windows PowerShell):
# Point to your DB (Render example uses DATABASE_URL)
$env:DATABASE_URL = "postgresql://user:pass@host:5432/db?sslmode=require"

# Create tables only
python _init_db.py

# Drop and recreate all tables
python _init_db.py --drop

# Create tables and seed demo users
python _init_db.py --seed-demo

# Drop, recreate, and seed
python _init_db.py --drop --seed-demo
"""

from __future__ import annotations
import argparse
from datetime import date, datetime
from app import create_app
from models import db
from models.user import User
from models.employee import Employee
from models.department import Department
from models.holiday import Holiday


def upsert_admin_user(email: str, password: str) -> None:
    admin = User.query.filter_by(email=email).first()
    if admin is None:
        admin = User(
            email=email,
            name="Admin User",
            role="admin",
            created_by="_init_db",
        )
        db.session.add(admin)
    
    admin.set_password(password)
    admin.set_permissions(["all"])  # full access


def upsert_demo_employee_user(email: str, password: str) -> None:
    demo_emp_id = "EMPDEMO001"
    
    employee = Employee.query.filter_by(employee_id=demo_emp_id).first()
    if employee is None:
        employee = Employee(
            employee_id=demo_emp_id,
            first_name="Demo",
            last_name="Employee",
            email=email,
            designation="Associate",
            employment_status="Active",
            department_id="IT",  # Assign to IT department
            created_by="_init_db",
        )
        db.session.add(employee)
    
    user = User.query.filter_by(email=email).first()
    if user is None:
        user = User(
            email=email,
            name="Demo Employee",
            role="employee",
            employee_id=demo_emp_id,
            created_by="_init_db",
        )
        db.session.add(user)
    
    user.employee_id = demo_emp_id
    user.set_password(password)
    user.set_permissions(["view_profile", "mark_attendance", "view_attendance"])


def seed_departments() -> None:
    """Seed default departments"""
    departments = [
        {
            "department_id": "HR",
            "department_name": "HR",
            "description": "Handles employee relations, recruitment, training, and organizational development."
        },
        {
            "department_id": "IT",
            "department_name": "IT",
            "description": "Responsible for managing technology infrastructure, software development, and IT support."
        },
        {
            "department_id": "Finance",
            "department_name": "Finance",
            "description": "Manages financial planning, accounting, budgeting, and financial reporting."
        },
        {
            "department_id": "Marketing",
            "department_name": "Marketing",
            "description": "Responsible for market research, advertising, brand management, and customer engagement."
        },
        {
            "department_id": "Operations",
            "department_name": "Operations",
            "description": "Oversees daily business operations, process optimization, and operational efficiency."
        },
        {
            "department_id": "Sales",
            "department_name": "Sales",
            "description": "Manages customer acquisition, sales processes, and revenue generation."
        },
        {
            "department_id": "Engineering",
            "department_name": "Engineering",
            "description": "Handles product development, technical design, and engineering solutions."
        },
        {
            "department_id": "Customer Support",
            "department_name": "Customer Support",
            "description": "Provides customer service, technical support, and client relationship management."
        },
        {
            "department_id": "Legal",
            "department_name": "Legal",
            "description": "Manages legal compliance, contracts, regulatory affairs, and legal risk management."
        },
        {
            "department_id": "Administration",
            "department_name": "Administration",
            "description": "Handles administrative functions, office management, and general support services."
        }
    ]
    
    for dept_data in departments:
        dept = Department.query.filter_by(department_id=dept_data["department_id"]).first()
        if dept is None:
            dept = Department(
                department_id=dept_data["department_id"],
                department_name=dept_data["department_name"],
                description=dept_data["description"],
                is_active=True,
                created_by="_init_db"
            )
            db.session.add(dept)
    
    print("✅ Seeded departments")


def seed_holidays() -> None:
    """Seed default holidays for the current year"""
    current_year = datetime.now().year
    
    holidays = [
        {
            "holiday_name": "New Year's Day",
            "holiday_date": date(current_year, 1, 1),
            "holiday_type": "National",
            "description": "First day of the year",
            "is_paid": True,
            "is_mandatory": True
        },
        {
            "holiday_name": "Republic Day",
            "holiday_date": date(current_year, 1, 26),
            "holiday_type": "National", 
            "description": "Indian Republic Day",
            "is_paid": True,
            "is_mandatory": True
        },
        {
            "holiday_name": "Independence Day",
            "holiday_date": date(current_year, 8, 15),
            "holiday_type": "National",
            "description": "Indian Independence Day",
            "is_paid": True,
            "is_mandatory": True
        },
        {
            "holiday_name": "Gandhi Jayanti",
            "holiday_date": date(current_year, 10, 2),
            "holiday_type": "National",
            "description": "Mahatma Gandhi's Birthday",
            "is_paid": True,
            "is_mandatory": True
        },
        {
            "holiday_name": "Christmas Day",
            "holiday_date": date(current_year, 12, 25),
            "holiday_type": "National",
            "description": "Christian festival celebrating the birth of Jesus Christ",
            "is_paid": True,
            "is_mandatory": True
        },
        {
            "holiday_name": "Company Foundation Day",
            "holiday_date": date(current_year, 4, 15),
            "holiday_type": "Company",
            "description": "Anniversary of company establishment",
            "is_paid": True,
            "is_mandatory": False
        },
        {
            "holiday_name": "Good Friday",
            "holiday_date": date(current_year, 3, 29),  # Note: This varies each year
            "holiday_type": "Regional",
            "description": "Christian commemoration of Jesus Christ's crucifixion",
            "is_paid": True,
            "is_mandatory": False
        }
    ]
    
    for holiday_data in holidays:
        # Check if holiday already exists for this date
        existing_holiday = Holiday.query.filter_by(holiday_date=holiday_data["holiday_date"]).first()
        if existing_holiday is None:
            holiday = Holiday(
                holiday_name=holiday_data["holiday_name"],
                holiday_date=holiday_data["holiday_date"],
                holiday_type=holiday_data["holiday_type"],
                description=holiday_data["description"],
                is_paid=holiday_data["is_paid"],
                is_mandatory=holiday_data["is_mandatory"],
                is_active=True,
                created_by="_init_db"
            )
            db.session.add(holiday)
    
    print("✅ Seeded holidays")


def init_database(drop: bool, seed_demo: bool) -> int:
    # Use minimal app without registering blueprints to avoid heavy imports (pandas)
    app = create_app(register_blueprints=False)
    
    with app.app_context():
        try:
            if drop:
                print("Dropping all tables...")
                db.drop_all()
            
            print("Creating all tables (if not exist)...")
            db.create_all()
            
            if seed_demo:
                print("Seeding demo data...")
                
                # Seed departments first (as employees might reference them)
                seed_departments()
                
                # Seed holidays
                seed_holidays()
                
                # Seed users
                upsert_admin_user("admin@company.com", "admin123")
                upsert_demo_employee_user("employee@company.com", "emp123")
                
                db.session.commit()
                
                print("✅ Database initialized successfully with demo data.")
                print("Demo credentials:")
                print("  Admin: admin@company.com / admin123")
                print("  Employee: employee@company.com / emp123")
            else:
                print("✅ Database initialized successfully.")
            
            return 0
            
        except Exception as exc:  # noqa: BLE001 - show full error
            try:
                db.session.rollback()
            except Exception:
                pass
            print(f"❌ Initialization failed: {exc}")
            return 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Initialize database tables and optionally seed demo users.")
    parser.add_argument("--drop", action="store_true", help="Drop all tables before creating them")
    parser.add_argument("--seed-demo", action="store_true", help="Seed demo admin/employee users, departments, and holidays")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    raise SystemExit(init_database(drop=args.drop, seed_demo=args.seed_demo))