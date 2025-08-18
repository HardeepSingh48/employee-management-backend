from models import db
from sqlalchemy.sql import func

class Department(db.Model):
    __tablename__ = "departments"

    department_id = db.Column(db.String(50), primary_key=True)
    department_name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(500))
    is_active = db.Column(db.Boolean, default=True)
    
    # Audit fields
    created_date = db.Column(db.Date, server_default=func.current_date())
    created_by = db.Column(db.String(100))
    updated_date = db.Column(db.Date, onupdate=func.current_date())
    updated_by = db.Column(db.String(100))

    def __repr__(self):
        return f"<Department {self.department_id} - {self.department_name}>"
