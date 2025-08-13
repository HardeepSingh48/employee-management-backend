from models import db
from sqlalchemy.sql import func

class Attendance(db.Model):
    __tablename__ = "attendance"

    attendance_id = db.Column(db.String(50), primary_key=True)
    employee_id = db.Column(db.String(50), db.ForeignKey("employees.employee_id"), nullable=False)
    attendance_date = db.Column(db.Date, nullable=False)
    check_in_time = db.Column(db.DateTime)
    check_out_time = db.Column(db.DateTime)
    attendance_status = db.Column(db.String(20), db.CheckConstraint("attendance_status IN ('Absent', 'Present', 'Late')"))

    # Audit fields
    created_date = db.Column(db.Date, server_default=func.current_date())
    created_by = db.Column(db.String(100))
    updated_date = db.Column(db.Date, onupdate=func.current_date())
    updated_by = db.Column(db.String(100))

    # Relationship
    employee = db.relationship("Employee", backref="attendance_records")

    def __repr__(self):
        return f"<Attendance {self.attendance_id} - {self.employee_id} - {self.attendance_date}>"