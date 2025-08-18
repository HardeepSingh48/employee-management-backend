from models import db
from sqlalchemy.sql import func
from datetime import datetime, time
import uuid

class Attendance(db.Model):
    __tablename__ = "attendance"

    attendance_id = db.Column(db.String(50), primary_key=True, default=lambda: str(uuid.uuid4()))
    employee_id = db.Column(db.String(50), db.ForeignKey("employees.employee_id"), nullable=False)
    attendance_date = db.Column(db.Date, nullable=False)
    check_in_time = db.Column(db.DateTime)
    check_out_time = db.Column(db.DateTime)
    attendance_status = db.Column(db.String(20),
                                db.CheckConstraint("attendance_status IN ('Present', 'Absent', 'Late', 'Half Day', 'Holiday', 'Leave')"),
                                default='Present')

    # Additional attendance fields
    overtime_hours = db.Column(db.Float, default=0.0)
    late_minutes = db.Column(db.Integer, default=0)
    early_departure_minutes = db.Column(db.Integer, default=0)
    total_hours_worked = db.Column(db.Float, default=8.0)
    is_holiday = db.Column(db.Boolean, default=False)
    is_weekend = db.Column(db.Boolean, default=False)
    remarks = db.Column(db.Text)
    marked_by = db.Column(db.String(20), default='employee')
    is_approved = db.Column(db.Boolean, default=True)
    approved_by = db.Column(db.String(100))
    approved_date = db.Column(db.DateTime)

    # Audit fields
    created_date = db.Column(db.Date, server_default=func.current_date())
    created_by = db.Column(db.String(100))
    updated_date = db.Column(db.Date, onupdate=func.current_date())
    updated_by = db.Column(db.String(100))

    # Relationship
    employee = db.relationship("Employee", backref="attendance_records")

    def to_dict(self):
        """Convert attendance record to dictionary"""
        return {
            'attendance_id': self.attendance_id,
            'employee_id': self.employee_id,
            'attendance_date': self.attendance_date.isoformat() if self.attendance_date else None,
            'check_in_time': self.check_in_time.isoformat() if self.check_in_time else None,
            'check_out_time': self.check_out_time.isoformat() if self.check_out_time else None,
            'attendance_status': self.attendance_status,
            'overtime_hours': self.overtime_hours,
            'late_minutes': self.late_minutes,
            'early_departure_minutes': self.early_departure_minutes,
            'total_hours_worked': self.total_hours_worked,
            'is_holiday': self.is_holiday,
            'is_weekend': self.is_weekend,
            'remarks': self.remarks,
            'marked_by': self.marked_by,
            'is_approved': self.is_approved,
            'approved_by': self.approved_by,
            'approved_date': self.approved_date.isoformat() if self.approved_date else None,
            'created_date': self.created_date.isoformat() if self.created_date else None,
            'created_by': self.created_by,
            'updated_date': self.updated_date.isoformat() if self.updated_date else None,
            'updated_by': self.updated_by
        }

    @staticmethod
    def calculate_work_hours(check_in_time, check_out_time):
        """Calculate total work hours between check-in and check-out"""
        if not check_in_time or not check_out_time:
            return 8.0  # Default work hours

        if isinstance(check_in_time, str):
            check_in_time = datetime.fromisoformat(check_in_time.replace('Z', '+00:00'))
        if isinstance(check_out_time, str):
            check_out_time = datetime.fromisoformat(check_out_time.replace('Z', '+00:00'))

        time_diff = check_out_time - check_in_time
        return round(time_diff.total_seconds() / 3600, 2)  # Convert to hours

    @staticmethod
    def is_late(check_in_time, standard_start_time=time(9, 0)):
        """Check if employee is late and calculate late minutes"""
        if not check_in_time:
            return False, 0

        if isinstance(check_in_time, str):
            check_in_time = datetime.fromisoformat(check_in_time.replace('Z', '+00:00'))

        check_in_time_only = check_in_time.time()

        if check_in_time_only > standard_start_time:
            # Calculate late minutes
            standard_datetime = datetime.combine(check_in_time.date(), standard_start_time)
            late_minutes = int((check_in_time - standard_datetime).total_seconds() / 60)
            return True, late_minutes

        return False, 0

    def __repr__(self):
        return f"<Attendance {self.attendance_id} - {self.employee_id} - {self.attendance_date}>"