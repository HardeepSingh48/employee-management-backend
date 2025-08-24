from models import db
from sqlalchemy.sql import func

class Site(db.Model):
    __tablename__ = 'sites'
    
    site_id = db.Column(db.String(50), primary_key=True)
    site_name = db.Column(db.String(200), nullable=False)
    location = db.Column(db.String(500))
    state = db.Column(db.String(100))
    is_active = db.Column(db.Boolean, default=True)
    
    # Audit fields
    created_date = db.Column(db.Date, server_default=func.current_date())
    created_by = db.Column(db.String(100))
    updated_date = db.Column(db.Date, onupdate=func.current_date())
    updated_by = db.Column(db.String(100))
    
    def to_dict(self):
        return {
            'site_id': self.site_id,
            'site_name': self.site_name,
            'location': self.location,
            'state': self.state,
            'is_active': self.is_active,
            'created_date': self.created_date.isoformat() if self.created_date else None
        }
    
    def __repr__(self):
        return f"<Site {self.site_id} - {self.site_name}>"