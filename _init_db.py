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
from app import create_app
from models import db
from models.user import User
from models.employee import Employee


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
                print("Seeding demo users...")
                upsert_admin_user("admin@company.com", "admin123")
                upsert_demo_employee_user("employee@company.com", "emp123")

            db.session.commit()
            print("✅ Database initialized successfully.")
            if seed_demo:
                print("Demo credentials:")
                print("  Admin:    admin@company.com / admin123")
                print("  Employee: employee@company.com / emp123")
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
    parser.add_argument("--seed-demo", action="store_true", help="Seed demo admin/employee users")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    raise SystemExit(init_database(drop=args.drop, seed_demo=args.seed_demo))


