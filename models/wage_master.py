from models import db
from sqlalchemy.sql import func

class WageMaster(db.Model):
    __tablename__ = "wage_masters"

    id = db.Column(db.Integer, primary_key=True, index=True)
    salary_code = db.Column(db.String(50), unique=True, nullable=False, index=True)

    # New foreign key column
    site_id = db.Column(db.String(50), db.ForeignKey("sites.site_id"), nullable=False)

    rank = db.Column(db.String(50), nullable=False)
    state = db.Column(db.String(50), nullable=False)
    base_wage = db.Column(db.Float, nullable=False)
    skill_level = db.Column(db.String(50), nullable=False)  
    is_active = db.Column(db.Boolean, default=True)

    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now())
    updated_at = db.Column(db.DateTime(timezone=True), onupdate=func.now())
    created_by = db.Column(db.String(100))

    # Relationship
    site = db.relationship("Site", backref="wage_masters")

    def __repr__(self):
        return f"<WageMaster(salary_code='{self.salary_code}', site='{self.site_id}', rank='{self.rank}')>"

