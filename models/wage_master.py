from models import db
from sqlalchemy.sql import func

class WageMaster(db.Model):
    __tablename__ = "wage_masters"

    id = db.Column(db.Integer, primary_key=True, index=True)
    salary_code = db.Column(db.String(50), unique=True, nullable=False, index=True)
    site_name = db.Column(db.String(100), nullable=False)
    rank = db.Column(db.String(50), nullable=False)
    state = db.Column(db.String(50), nullable=False)
    base_wage = db.Column(db.Float, nullable=False)
    skill_level = db.Column(db.String(50), nullable=False)  # Highly Skilled, Skilled, Semi-Skilled, Un-Skilled
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now())
    updated_at = db.Column(db.DateTime(timezone=True), onupdate=func.now())
    created_by = db.Column(db.String(100))

    def __repr__(self):
        return f"<WageMaster(salary_code='{self.salary_code}', site='{self.site_name}', rank='{self.rank}')>"

