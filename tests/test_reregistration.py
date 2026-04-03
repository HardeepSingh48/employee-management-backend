"""
test_reregistration.py — Tests for the employee re-registration / reactivation flow.

Verifies that:
  - Registering with the same Aadhaar as an ACTIVE employee → 409
  - Registering with the same phone as an ACTIVE employee → 409 (fallback)
  - Registering with the same Aadhaar as a DELETED employee → 200 reactivated=True
  - Registering with the same phone as a DELETED employee → 200 reactivated=True (fallback)
  - Reactivation returns the SAME employee_id (not a new one)
  - Reactivation updates employment details from the new payload
  - A brand-new Aadhaar/phone creates a fresh employee (reactivated=False)
"""
import pytest
from models.employee import Employee
from .conftest import make_employee


# Minimal registration payload factory
def reg_payload(**overrides):
    base = {
        "first_name": "Returning",
        "last_name": "Employee",
        "adhar_number": "999988887777",
        "phone_number": "9876543210",
        "employment_status": "Active",
        "designation": "Worker",
    }
    base.update(overrides)
    return base


class TestDuplicateActiveRejection:
    """Active employees with same Aadhaar/phone must be rejected (409)."""

    def test_duplicate_aadhaar_active_employee_rejected(self, client, auth_headers, db):
        """Registering with an existing active Aadhaar must return 409."""
        emp = make_employee(db, adhar_number="111122223333")

        resp = client.post(
            "/api/employees/register",
            json=reg_payload(adhar_number="111122223333", phone_number="9111111111"),
            headers=auth_headers,
        )
        assert resp.status_code == 409
        data = resp.get_json()
        assert data["success"] is False
        assert str(emp.employee_id) in data["message"], \
            "Error message should include the existing employee_id"

    def test_duplicate_phone_active_employee_rejected(self, client, auth_headers, db):
        """Registering with an existing active phone (no Aadhaar match) must return 409."""
        emp = make_employee(db, adhar_number="UNIQUEADHAR01", phone_number="9222222222")

        resp = client.post(
            "/api/employees/register",
            json=reg_payload(adhar_number="UNIQUEADHAR99", phone_number="9222222222"),
            headers=auth_headers,
        )
        assert resp.status_code == 409
        data = resp.get_json()
        assert data["success"] is False
        assert str(emp.employee_id) in data["message"]


class TestReactivationByAadhaar:
    """Deleted employees should be reactivated when Aadhaar matches."""

    def test_reactivation_returns_same_employee_id(self, client, auth_headers, db):
        """Reactivation must return the ORIGINAL employee_id."""
        emp = make_employee(
            db,
            adhar_number="REAC111111111",
            phone_number="9300000001",
            is_deleted=True,
            employment_status="Inactive",
        )
        original_id = emp.employee_id

        resp = client.post(
            "/api/employees/register",
            json=reg_payload(
                adhar_number="REAC111111111",
                phone_number="9300000001",
                first_name="Rejoined",
                designation="Senior Worker",
            ),
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert data.get("reactivated") is True
        assert data["data"]["employee_id"] == original_id, \
            "Must return the same original employee_id"

    def test_reactivation_sets_active_status_in_db(self, client, auth_headers, db):
        """After reactivation the DB row must have is_deleted=False and Active status."""
        emp = make_employee(
            db,
            adhar_number="REAC222222222",
            phone_number="9300000002",
            is_deleted=True,
            employment_status="Inactive",
        )

        client.post(
            "/api/employees/register",
            json=reg_payload(adhar_number="REAC222222222", phone_number="9300000002"),
            headers=auth_headers,
        )

        db.session.expire_all()
        refreshed = Employee.query.get(emp.employee_id)
        assert refreshed.is_deleted is False
        assert refreshed.employment_status == "Active"
        assert refreshed.deleted_at is None

    def test_reactivation_updates_employment_fields(self, client, auth_headers, db):
        """New designation/department passed in payload must be applied on reactivation."""
        emp = make_employee(
            db,
            adhar_number="REAC333333333",
            phone_number="9300000003",
            is_deleted=True,
            employment_status="Inactive",
            designation="Old Designation",
        )

        client.post(
            "/api/employees/register",
            json=reg_payload(
                adhar_number="REAC333333333",
                phone_number="9300000003",
                designation="New Designation",
            ),
            headers=auth_headers,
        )

        db.session.expire_all()
        refreshed = Employee.query.get(emp.employee_id)
        assert refreshed.designation == "New Designation"


class TestReactivationByPhone:
    """Deleted employees should be reactivated when phone matches (fallback)."""

    def test_phone_fallback_reactivation(self, client, auth_headers, db):
        """With no Aadhaar match, phone fallback should reactivate the correct employee."""
        emp = make_employee(
            db,
            adhar_number="PHFB000000001",
            phone_number="9400000001",
            is_deleted=True,
            employment_status="Inactive",
        )
        original_id = emp.employee_id

        resp = client.post(
            "/api/employees/register",
            # Use a different Aadhaar (no match) but same phone
            json=reg_payload(
                adhar_number="000000000000",   # placeholder — treated as no value
                phone_number="9400000001",
            ),
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data.get("reactivated") is True
        assert data["data"]["employee_id"] == original_id


class TestFreshRegistration:
    """Brand-new employees (no match) should create a new record."""

    def test_new_employee_gets_reactivated_false(self, client, auth_headers, db):
        """Brand-new registration must return reactivated=False and a new employee_id."""
        resp = client.post(
            "/api/employees/register",
            json=reg_payload(
                adhar_number="BRAND00000001",
                phone_number="9500000001",
            ),
            headers=auth_headers,
        )
        # 201 for new employees
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["success"] is True
        assert data.get("reactivated") is False
