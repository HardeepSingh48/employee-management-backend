from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql import func
from werkzeug.security import generate_password_hash, check_password_hash
import uuid

# Import db after other imports to avoid circular import
from flask import current_app

# We'll get db from current_app context or define it locally
try:
    from models import db
except ImportError:
    db = SQLAlchemy()

class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.String(50), primary_key=True, default=lambda: str(uuid.uuid4()))
    employee_id = db.Column(db.String(50), db.ForeignKey("employees.employee_id"), nullable=True)
    
    # Authentication fields
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    
    # User details
    name = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), 
                    db.CheckConstraint("role IN ('admin', 'hr', 'manager', 'employee')"), 
                    nullable=False, default='employee')
    
    # Status and permissions
    is_active = db.Column(db.Boolean, default=True)
    is_verified = db.Column(db.Boolean, default=False)
    permissions = db.Column(db.Text)  # JSON string of permissions
    
    # Login tracking
    last_login = db.Column(db.DateTime)
    login_attempts = db.Column(db.Integer, default=0)
    locked_until = db.Column(db.DateTime)
    
    # Profile
    profile_image = db.Column(db.String(500))
    department = db.Column(db.String(100))
    
    # Audit fields
    created_date = db.Column(db.DateTime, server_default=func.now())
    created_by = db.Column(db.String(100))
    updated_date = db.Column(db.DateTime, onupdate=func.now())
    updated_by = db.Column(db.String(100))

    # Relationships
    employee = db.relationship("Employee", backref="user_account", foreign_keys=[employee_id])

    def set_password(self, password):
        """Set password hash"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Check password against hash"""
        return check_password_hash(self.password_hash, password)

    def get_permissions(self):
        """Get user permissions as list"""
        if self.permissions:
            import json
            try:
                return json.loads(self.permissions)
            except:
                return []
        return []

    def set_permissions(self, permissions_list):
        """Set user permissions from list"""
        import json
        self.permissions = json.dumps(permissions_list)

    def to_dict(self):
        """Convert user to dictionary for API responses"""
        return {
            'id': self.id,
            'employee_id': self.employee_id,
            'email': self.email,
            'name': self.name,
            'role': self.role,
            'is_active': self.is_active,
            'is_verified': self.is_verified,
            'permissions': self.get_permissions(),
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'profile_image': self.profile_image,
            'department': self.department,
            'created_date': self.created_date.isoformat() if self.created_date else None
        }

    def __repr__(self):
        return f"<User {self.email} - {self.role}>"
