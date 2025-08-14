from models import db
from sqlalchemy.sql import func
import uuid
from datetime import datetime

class Attendance(db.Model):
    __tablename__ = "attendance"

    attendance_id = db.Column(db.String(50), primary_key=True, default=lambda: str(uuid.uuid4()))
    employee_id = db.Column(db.String(50), db.ForeignKey("employees.employee_id"), nullable=False)
    attendance_date = db.Column(db.Date, nullable=False)

    # Time tracking
    check_in_time = db.Column(db.DateTime)
    check_out_time = db.Column(db.DateTime)

    # Attendance status with enhanced options
    attendance_status = db.Column(db.String(20),
        db.CheckConstraint("attendance_status IN ('Present', 'Absent', 'Late', 'Half Day', 'Holiday', 'Leave')"),
        nullable=False, default='Present')

    # Additional fields for salary calculation
    overtime_hours = db.Column(db.Float, default=0.0)  # Overtime hours worked
    late_minutes = db.Column(db.Integer, default=0)    # Minutes late
    early_departure_minutes = db.Column(db.Integer, default=0)  # Minutes left early

    # Work details
    total_hours_worked = db.Column(db.Float, default=8.0)  # Standard 8 hours
    is_holiday = db.Column(db.Boolean, default=False)      # Is this date a holiday
    is_weekend = db.Column(db.Boolean, default=False)      # Is this date a weekend

    # Notes and remarks
    remarks = db.Column(db.Text)  # Any special notes
    marked_by = db.Column(db.String(20), default='employee')  # 'employee', 'admin', 'system'

    # Approval workflow (for future use)
    is_approved = db.Column(db.Boolean, default=True)
    approved_by = db.Column(db.String(100))
    approved_date = db.Column(db.DateTime)

    # Audit fields
    created_date = db.Column(db.DateTime, server_default=func.now())
    created_by = db.Column(db.String(100))
    updated_date = db.Column(db.DateTime, onupdate=func.now())
    updated_by = db.Column(db.String(100))

    # Relationship
    employee = db.relationship("Employee", backref="attendance_records")

    # Unique constraint to prevent duplicate attendance for same employee on same date
    __table_args__ = (
        db.UniqueConstraint('employee_id', 'attendance_date', name='unique_employee_date_attendance'),
    )

    def __repr__(self):
        return f"<Attendance {self.attendance_id} - {self.employee_id} - {self.attendance_date} - {self.attendance_status}>"

    def to_dict(self):
        """Convert attendance record to dictionary for API responses"""
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
            'created_date': self.created_date.isoformat() if self.created_date else None
        }

    @staticmethod
    def calculate_work_hours(check_in_time, check_out_time):
        """Calculate total work hours from check-in and check-out times"""
        if not check_in_time or not check_out_time:
            return 0.0

        time_diff = check_out_time - check_in_time
        return round(time_diff.total_seconds() / 3600, 2)  # Convert to hours

    @staticmethod
    def is_late(check_in_time, standard_start_time="09:00"):
        """Check if employee is late based on standard start time"""
        if not check_in_time:
            return False, 0

        # Convert standard_start_time to datetime for comparison
        standard_time = datetime.strptime(standard_start_time, "%H:%M").time()
        standard_datetime = datetime.combine(check_in_time.date(), standard_time)

        if check_in_time > standard_datetime:
            late_minutes = int((check_in_time - standard_datetime).total_seconds() / 60)
            return True, late_minutes

        return False, 0