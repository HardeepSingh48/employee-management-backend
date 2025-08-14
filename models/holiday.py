from models import db
from sqlalchemy.sql import func
import uuid

class Holiday(db.Model):
    __tablename__ = "holidays"

    holiday_id = db.Column(db.String(50), primary_key=True, default=lambda: str(uuid.uuid4()))
    holiday_name = db.Column(db.String(100), nullable=False)
    holiday_date = db.Column(db.Date, nullable=False, unique=True)
    holiday_type = db.Column(db.String(20), 
        db.CheckConstraint("holiday_type IN ('National', 'Regional', 'Company', 'Optional')"), 
        nullable=False, default='Company')
    
    # Holiday details
    description = db.Column(db.Text)
    is_paid = db.Column(db.Boolean, default=True)  # Is this a paid holiday
    is_mandatory = db.Column(db.Boolean, default=True)  # Is attendance mandatory (for optional holidays)
    is_active = db.Column(db.Boolean, default=True)
    
    # Location/Department specific (optional)
    applicable_departments = db.Column(db.Text)  # JSON string of department IDs
    applicable_locations = db.Column(db.Text)    # JSON string of locations
    
    # Audit fields
    created_date = db.Column(db.DateTime, server_default=func.now())
    created_by = db.Column(db.String(100))
    updated_date = db.Column(db.DateTime, onupdate=func.now())
    updated_by = db.Column(db.String(100))

    def __repr__(self):
        return f"<Holiday {self.holiday_name} - {self.holiday_date}>"
    
    def to_dict(self):
        """Convert holiday record to dictionary for API responses"""
        return {
            'holiday_id': self.holiday_id,
            'holiday_name': self.holiday_name,
            'holiday_date': self.holiday_date.isoformat() if self.holiday_date else None,
            'holiday_type': self.holiday_type,
            'description': self.description,
            'is_paid': self.is_paid,
            'is_mandatory': self.is_mandatory,
            'is_active': self.is_active,
            'created_date': self.created_date.isoformat() if self.created_date else None
        }
    
    @staticmethod
    def is_holiday(date):
        """Check if a given date is a holiday"""
        holiday = Holiday.query.filter_by(holiday_date=date, is_active=True).first()
        return holiday is not None, holiday
    
    @staticmethod
    def get_holidays_for_month(year, month):
        """Get all holidays for a specific month"""
        from datetime import date
        start_date = date(year, month, 1)
        if month == 12:
            end_date = date(year + 1, 1, 1)
        else:
            end_date = date(year, month + 1, 1)
        
        return Holiday.query.filter(
            Holiday.holiday_date >= start_date,
            Holiday.holiday_date < end_date,
            Holiday.is_active == True
        ).all()
