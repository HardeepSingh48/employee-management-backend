from models import db
from sqlalchemy.sql import func

class AccountDetails(db.Model):
    __tablename__ = "account_details"

    id = db.Column(db.Integer, primary_key=True)
    emp_id = db.Column(db.String(50), db.ForeignKey("employees.employee_id"), nullable=False)
    account_number = db.Column(db.String(50), nullable=False)
    ifsc_code = db.Column(db.String(20), nullable=False)
    bank_name = db.Column(db.String(100))
    branch_name = db.Column(db.String(100))
    
    # Audit fields
    created_date = db.Column(db.Date, server_default=func.current_date())
    created_by = db.Column(db.String(100))
    updated_date = db.Column(db.Date, onupdate=func.current_date())
    updated_by = db.Column(db.String(100))

    # Relationship
    employee = db.relationship("Employee", backref="account_details")

    def __repr__(self):
        return f"<AccountDetails {self.emp_id} - {self.bank_name}>"
