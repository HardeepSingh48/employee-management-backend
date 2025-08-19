#!/usr/bin/env python3
"""
Seed demo users into the configured database.

Usage:
  # Option A: Use individual DB_* env vars (as used by config.py)
  export DB_HOST=... DB_PORT=5432 DB_NAME=... DB_USER=... DB_PASSWORD=...
  python seed_demo_users.py

  # Option B: Use a full DATABASE_URL (postgresql://user:pass@host:port/db)
  export DATABASE_URL=postgresql://...
  python seed_demo_users.py

Environment overrides for credentials (optional):
  ADMIN_EMAIL, ADMIN_PASSWORD, EMP_EMAIL, EMP_PASSWORD
"""

import os
from app import create_app
from models import db
from models.user import User
from models.employee import Employee


def upsert_admin(admin_email: str, admin_password: str) -> None:
    admin = User.query.filter_by(email=admin_email).first()
    if admin:
        # Ensure role/permissions and password are set as expected
        admin.role = "admin"
        admin.set_permissions(["all"])  # full access
        admin.set_password(admin_password)
    else:
        admin = User(
            email=admin_email,
            name="Admin User",
            role="admin",
            created_by="seed_script",
        )
        admin.set_password(admin_password)
        admin.set_permissions(["all"])  # full access
        db.session.add(admin)


def upsert_employee_user(emp_email: str, emp_password: str) -> None:
    # Ensure a minimal employee row exists
    demo_employee_id = "EMPDEMO001"
    employee = Employee.query.filter_by(employee_id=demo_employee_id).first()
    if not employee:
        employee = Employee(
            employee_id=demo_employee_id,
            first_name="Demo",
            last_name="Employee",
            email=emp_email,
            designation="Associate",
            employment_status="Active",
            created_by="seed_script",
        )
        db.session.add(employee)

    emp_user = User.query.filter_by(email=emp_email).first()
    if emp_user:
        emp_user.role = "employee"
        emp_user.employee_id = demo_employee_id
        emp_user.set_permissions([
            "view_profile",
            "mark_attendance",
            "view_attendance",
        ])
        emp_user.set_password(emp_password)
    else:
        emp_user = User(
            email=emp_email,
            name="Demo Employee",
            role="employee",
            employee_id=demo_employee_id,
            created_by="seed_script",
        )
        emp_user.set_password(emp_password)
        emp_user.set_permissions([
            "view_profile",
            "mark_attendance",
            "view_attendance",
        ])
        db.session.add(emp_user)


def main() -> int:
    # Allow overriding demo credentials via env
    admin_email = os.getenv("ADMIN_EMAIL", "admin@company.com")
    admin_password = os.getenv("ADMIN_PASSWORD", "admin123")
    emp_email = os.getenv("EMP_EMAIL", "employee@company.com")
    emp_password = os.getenv("EMP_PASSWORD", "emp123")

    # Use minimal app without registering blueprints to avoid heavy imports (pandas)
    app = create_app(register_blueprints=False)
    with app.app_context():
        try:
            upsert_admin(admin_email, admin_password)
            upsert_employee_user(emp_email, emp_password)
            db.session.commit()
            print("✅ Demo users seeded/updated successfully.")
            print(f"  Admin:    {admin_email} / {admin_password}")
            print(f"  Employee: {emp_email} / {emp_password}")
            return 0
        except Exception as e:
            try:
                db.session.rollback()
            except Exception:
                pass
            print(f"❌ Seeding failed: {e}")
            return 1


if __name__ == "__main__":
    raise SystemExit(main())


