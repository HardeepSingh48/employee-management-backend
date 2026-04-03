"""
conftest.py — pytest fixtures for the employee management backend.

This file sets up a clean environment for every test run:
1. It patches the Postgres-specific startup functions so they don't crash on SQLite.
2. It uses an in-memory SQLite database for speed and isolation.
3. It seeds a default admin user for authentication tests.
4. it provides helper fixtures for employee creation and auth headers.
"""
import os
import pytest
import jwt
from unittest.mock import patch
from datetime import datetime, timedelta

# 1. Environment Overrides (Must happen before any app-related imports)
os.environ["SECRET_KEY"] = "ci-test-secret-key-12345"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["FLASK_ENV"] = "testing"
os.environ["CREATE_APP_ON_IMPORT"] = "0"

from app import create_app
from models import db as _db
from models.employee import Employee
from models.user import User
from models.deduction import Deduction

@pytest.fixture(scope="session")
def app():
    # Patch the sequence sync because it uses Postgres-specific raw SQL
    with patch("app.synchronize_employee_id_sequence", return_value=None):
        test_app = create_app(register_blueprints=True)
        
        test_app.config.update({
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "SQLALCHEMY_TRACK_MODIFICATIONS": False,
        })

        with test_app.app_context():
            _db.create_all()
            # Seed our test admin
            if not User.query.filter_by(email="admin@test.com").first():
                admin = User(
                    email="admin@test.com",
                    username="testadmin",
                    name="Test Admin",
                    role="admin1",
                    is_active=True,
                    is_verified=True
                )
                admin.set_password("AdminPass123!")
                admin.set_permissions(["all"])
                _db.session.add(admin)
                _db.session.commit()
            
            yield test_app
            _db.drop_all()

@pytest.fixture()
def client(app):
    return app.test_client()

@pytest.fixture()
def db(app):
    with app.app_context():
        yield _db
        _db.session.rollback()

@pytest.fixture()
def auth_headers(app):
    """Generates a valid JWT for the test admin."""
    with app.app_context():
        user = User.query.filter_by(email="admin@test.com").first()
        payload = {
            'user_id': user.id,
            'email': user.email,
            'role': user.role,
            'exp': datetime.utcnow() + timedelta(hours=1)
        }
        token = jwt.encode(payload, os.environ["SECRET_KEY"], algorithm='HS256')
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

# Helper to create employees quickly in tests
def make_employee(db_session, **kwargs):
    emp_id = kwargs.pop('employee_id', 99999 + int(datetime.now().timestamp() % 10000))
    defaults = {
        "employee_id": emp_id,
        "first_name": "Test",
        "last_name": "User",
        "adhar_number": f"12345678{emp_id}",
        "phone_number": f"99999{str(emp_id)[-5:]}",
        "employment_status": "Active",
        "is_deleted": False
    }
    defaults.update(kwargs)
    emp = Employee(**defaults)
    db_session.session.add(emp)
    db_session.session.commit()
    return emp
