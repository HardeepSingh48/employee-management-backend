from models import db
from datetime import datetime

class Site(db.Model):
    __tablename__ = 'sites'
    
    site_id = db.Column(db.String(50), primary_key=True)
    site_name = db.Column(db.String(200), nullable=False)
    location = db.Column(db.String(500))
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    radius_metres = db.Column(db.Integer, nullable=True, default=200)
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
            'latitude': self.latitude,
            'longitude': self.longitude,
            'radius_metres': self.radius_metres,
            'state': self.state,
            'is_active': self.is_active,
            'created_date': self.created_date.isoformat() if self.created_date else None,
            'created_by': self.created_by,
            'updated_date': self.updated_date.isoformat() if self.updated_date else None,
            'updated_by': self.updated_by
        }
    
    def __repr__(self):
        return f"<Site {self.site_id} - {self.site_name}>"
    
    @classmethod
    def get_or_create_site(cls, site_name: str, state: str, created_by: str = "system") -> "Site":
        """Get a site by name (case-insensitive, trimmed) or create it if not found."""
        from sqlalchemy import func
        import uuid
        
        site_name_clean = site_name.strip()
        state_clean = state.strip() if state else "Unknown"
        
        # Look for site by name (case-insensitive, trimmed)
        site = cls.query.filter(
            func.trim(func.lower(cls.site_name)) == func.trim(func.lower(site_name_clean))
        ).first()
        
        if not site:
            # Create a new site
            site_id = f"SITE-{uuid.uuid4().hex[:8].upper()}"
            site = cls(
                site_id=site_id,
                site_name=site_name_clean,
                state=state_clean,
                is_active=True,
                created_by=created_by
            )
            db.session.add(site)
            # Flush to get the site_id and ensure it's queryable in the transaction
            db.session.flush()
            
        return site

    @classmethod
    def cleanup_if_orphaned(cls, site_id: str) -> bool:
        """Delete a site if it has no active wage masters and no employees.
        
        Returns True if the site was deleted, False if it still has references.
        Should be called after deleting/deactivating wage masters.
        """
        from models.wage_master import WageMaster
        from models.employee import Employee

        site = cls.query.get(site_id)
        if not site:
            return False

        active_wage_masters = WageMaster.query.filter_by(
            site_id=site_id, is_active=True
        ).count()

        if active_wage_masters > 0:
            return False  # Still has salary codes — keep the site

        employee_count = Employee.query.filter_by(site_id=site_id).count()
        if employee_count > 0:
            return False  # Still has employees — keep the site

        db.session.delete(site)
        return True

