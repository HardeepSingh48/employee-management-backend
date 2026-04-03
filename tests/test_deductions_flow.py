"""
test_deductions_flow.py — Tests for deduction continuity through soft delete / reactivation.

Verifies that:
  - GET /deductions/ hides deductions when the employee is soft-deleted
  - GET /deductions/ shows deductions again after the employee is reactivated
  - Deduction rows themselves are never removed during soft delete
"""
import pytest
from models.deduction import Deduction
from models.employee import Employee
from .conftest import make_employee
import uuid
from datetime import date


def create_deduction(db_session, employee_id, deduction_type="Test Loan"):
    """Helper: create and persist a deduction for an employee."""
    ded = Deduction(
        deduction_id=str(uuid.uuid4()),
        employee_id=employee_id,
        deduction_type=deduction_type,
        total_amount=12000.00,
        months=12,
        start_month=date(2025, 1, 1),
        created_by="test",
    )
    db_session.session.add(ded)
    db_session.session.commit()
    return ded


class TestDeductionContinuity:
    """Deduction rows must survive soft delete and remain hidden until reactivation."""

    def test_deductions_row_survives_soft_delete(self, client, auth_headers, db):
        """Deduction DB rows must not be deleted when employee is soft-deleted."""
        emp = make_employee(db)
        create_deduction(db, emp.employee_id)

        # Soft delete the employee
        client.delete(f"/api/employees/{emp.employee_id}", headers=auth_headers)

        # Row must still exist in deductions table
        rows = Deduction.query.filter_by(employee_id=emp.employee_id).all()
        assert len(rows) == 1, "Deduction row must survive the soft delete"

    def test_deductions_hidden_when_employee_soft_deleted(self, client, auth_headers, db):
        """GET /deductions/ must not return deductions for soft-deleted employees."""
        emp = make_employee(db, is_deleted=True, employment_status="Inactive")
        create_deduction(db, emp.employee_id, deduction_type="HiddenLoan")

        resp = client.get("/api/deductions/", headers=auth_headers)
        assert resp.status_code == 200
        deductions_data = resp.get_json().get("data", [])
        emp_ids = [d.get("employee_id") for d in deductions_data]
        assert emp.employee_id not in emp_ids, \
            "Deductions for soft-deleted employee must be hidden from the list"

    def test_deductions_reappear_after_reactivation(self, client, auth_headers, db):
        """After reactivating a soft-deleted employee, their deductions reappear."""
        emp = make_employee(
            db,
            adhar_number="DED00000001",
            phone_number="9600000001",
            is_deleted=True,
            employment_status="Inactive",
        )
        create_deduction(db, emp.employee_id, deduction_type="ReappearLoan")

        # Verify deductions are hidden
        resp_before = client.get("/api/deductions/", headers=auth_headers)
        ids_before = [d.get("employee_id") for d in resp_before.get_json().get("data", [])]
        assert emp.employee_id not in ids_before

        # Reactivate the employee via re-registration
        client.post(
            "/api/employees/register",
            json={
                "first_name": "Reactivated",
                "last_name": "Employee",
                "adhar_number": "DED00000001",
                "phone_number": "9600000001",
            },
            headers=auth_headers,
        )

        # Verify DB is_deleted is now False
        db.session.expire_all()
        assert Employee.query.get(emp.employee_id).is_deleted is False

        # Now deductions should be visible again
        resp_after = client.get("/api/deductions/", headers=auth_headers)
        ids_after = [d.get("employee_id") for d in resp_after.get_json().get("data", [])]
        assert emp.employee_id in ids_after, \
            "Deductions must reappear in the list after employee reactivation"

    def test_deduction_count_unchanged_through_cycle(self, client, auth_headers, db):
        """The number of deduction rows must be identical before delete and after reactivation."""
        emp = make_employee(
            db,
            adhar_number="DED00000002",
            phone_number="9600000002",
        )
        create_deduction(db, emp.employee_id, "Loan A")
        create_deduction(db, emp.employee_id, "Loan B")

        count_before = Deduction.query.filter_by(employee_id=emp.employee_id).count()
        assert count_before == 2

        # Soft delete
        client.delete(f"/api/employees/{emp.employee_id}", headers=auth_headers)

        # Re-register (reactivate)
        client.post(
            "/api/employees/register",
            json={
                "first_name": "Back",
                "last_name": "Again",
                "adhar_number": "DED00000002",
                "phone_number": "9600000002",
            },
            headers=auth_headers,
        )

        count_after = Deduction.query.filter_by(employee_id=emp.employee_id).count()
        assert count_after == count_before, \
            "No deductions should be created or removed during the delete/reactivate cycle"
