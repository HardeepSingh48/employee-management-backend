from models import db
from sqlalchemy.sql import func
import uuid

class Deduction(db.Model):
    __tablename__ = "deductions"

    deduction_id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    employee_id = db.Column(db.Integer, db.ForeignKey("employees.employee_id"), nullable=False)
    deduction_type = db.Column(db.String(100), nullable=False)  # e.g., Clothes, Recovery, Loan
    total_amount = db.Column(db.Numeric(10, 2), nullable=False)
    months = db.Column(db.Integer, nullable=False)  # number of months to spread deduction
    start_month = db.Column(db.Date, nullable=False)  # first month from which deduction applies
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now())
    updated_at = db.Column(db.DateTime(timezone=True), onupdate=func.now())
    created_by = db.Column(db.String(100))
    updated_by = db.Column(db.String(100))

    # Relationship
    employee = db.relationship("Employee", backref="deductions")

    def __repr__(self):
        return f"<Deduction(deduction_id='{self.deduction_id}', employee_id='{self.employee_id}', type='{self.deduction_type}')>"

    def monthly_installment(self):
        """Calculate monthly installment amount"""
        if self.months <= 0:
            return 0
        return float(self.total_amount) / self.months

    def is_active_for_month(self, year, month):
        """Check if deduction is active for the given month"""
        from datetime import date
        current_date = date(year, month, 1)
        start_date = self.start_month
        
        # Calculate months difference
        months_diff = (current_date.year - start_date.year) * 12 + (current_date.month - start_date.month)
        
        # Deduction is active if current month is within the deduction period
        return 0 <= months_diff < self.months

    def get_installment_for_month(self, year, month):
        """Get installment amount for a specific month"""
        if self.is_active_for_month(year, month):
            return self.monthly_installment()
        return 0
