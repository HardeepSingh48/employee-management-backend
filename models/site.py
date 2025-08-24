from models import db
from datetime import datetime

class Site(db.Model):
    __tablename__ = 'sites'
    
    site_id = db.Column(db.String(50), primary_key=True)
    site_name = db.Column(db.String(200), nullable=False)
    location = db.Column(db.String(500))
    state = db.Column(db.String(100), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_date = db.Column(db.Date, default=datetime.utcnow().date)
    created_by = db.Column(db.String(100))
    updated_date = db.Column(db.Date)
    updated_by = db.Column(db.String(100))
    
    def to_dict(self):
        return {
            'site_id': self.site_id,
            'site_name': self.site_name,
            'location': self.location,
            'state': self.state,
            'is_active': self.is_active,
            'created_date': self.created_date.isoformat() if self.created_date else None,
            'created_by': self.created_by,
            'updated_date': self.updated_date.isoformat() if self.updated_date else None,
            'updated_by': self.updated_by
        }
    
    def __repr__(self):
        return f"<Site {self.site_id} - {self.site_name}>"