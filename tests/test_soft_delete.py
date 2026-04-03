"""
test_soft_delete.py — Tests for the soft delete employee feature.

Verifies that:
  - DELETE /employees/<id> returns 200 and marks is_deleted=True
  - The employee is hidden from GET /employees/ after deletion
  - GET /employees/<id> returns 404 for a soft-deleted employee
  - PUT /employees/<id> returns 404 for a soft-deleted employee
  - The account details and deductions are NOT removed by the delete
"""
import pytest
from models.employee import Employee
from models.deduction import Deduction
from .conftest import make_employee
import uuid
from datetime import date


class TestSoftDelete:
    """Tests for soft delete functionality."""

    def test_delete_returns_200_and_flags_employee(self, client, auth_headers, db):
        """DELETE /employees/<id> should return 200 and set is_deleted=True."""
        emp = make_employee(db)
        emp_id = emp.employee_id

        resp = client.delete(
            f"/api/employees/{emp_id}",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert "deactivated" in data["message"].lower()

        # Verify DB state
        db.session.expire_all()
        refreshed = Employee.query.get(emp_id)
        assert refreshed is not None, "Employee row must still exist (no hard delete)"
        assert refreshed.is_deleted is True
        assert refreshed.deleted_at is not None
        assert refreshed.employment_status == "Inactive"

    def test_deleted_employee_absent_from_list(self, client, auth_headers, db):
        """Soft-deleted employee must not appear in GET /employees/ list."""
        emp = make_employee(db)
        emp_id = emp.employee_id

        # Soft delete
        client.delete(f"/api/employees/{emp_id}", headers=auth_headers)

        # Fetch list
        resp = client.get("/api/employees/?page=1&per_page=100", headers=auth_headers)
        assert resp.status_code == 200
        ids = [e["employee_id"] for e in resp.get_json().get("data", [])]
        assert emp_id not in ids, "Deleted employee must be hidden from the list"

    def test_get_deleted_employee_returns_404(self, client, auth_headers, db):
        """GET /employees/<id> must return 404 for a soft-deleted employee."""
        emp = make_employee(db, is_deleted=True, employment_status="Inactive")

        resp = client.get(f"/api/employees/{emp.employee_id}", headers=auth_headers)
        assert resp.status_code == 404

    def test_put_deleted_employee_returns_404(self, client, auth_headers, db):
        """PUT /employees/<id> must return 404 for a soft-deleted employee."""
        emp = make_employee(db, is_deleted=True, employment_status="Inactive")

        resp = client.put(
            f"/api/employees/{emp.employee_id}",
            json={"first_name": "Updated"},
            headers=auth_headers,
        )
        assert resp.status_code == 404

    def test_deductions_survive_soft_delete(self, client, auth_headers, db):
        """Deductions linked to an employee must remain after soft delete."""
        emp = make_employee(db)

        # Attach a deduction
        ded = Deduction(
            deduction_id=str(uuid.uuid4()),
            employee_id=emp.employee_id,
            deduction_type="Test Loan",
            total_amount=5000.00,
            months=5,
            start_month=date(2025, 1, 1),
            created_by="test",
        )
        db.session.add(ded)
        db.session.commit()

        # Soft delete the employee
        resp = client.delete(f"/api/employees/{emp.employee_id}", headers=auth_headers)
        assert resp.status_code == 200

        # The deduction row must still exist
        surviving = Deduction.query.filter_by(employee_id=emp.employee_id).all()
        assert len(surviving) == 1, "Deduction row must survive soft delete"

    def test_include_deleted_query_param_shows_deleted(self, client, auth_headers, db):
        """GET /employees/?include_deleted=true must include soft-deleted employees."""
        emp = make_employee(db, is_deleted=True, employment_status="Inactive")
        emp_id = emp.employee_id

        resp = client.get(
            "/api/employees/?include_deleted=true&per_page=500",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        ids = [e["employee_id"] for e in resp.get_json().get("data", [])]
        assert emp_id in ids, "Deleted employee must appear with include_deleted=true"
