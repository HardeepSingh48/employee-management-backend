# routes/wages.py
from sqlalchemy.orm import Session
from models.wage_master import WageMaster, Employee
from typing import List, Optional
import re

class WageMasterService:
    def __init__(self, db: Session):
        self.db = db
    
    def generate_salary_code(self, site_name: str, rank: str, state: str) -> str:
        """
        Generate salary code from site name, rank, and state
        Format: [SITE_PREFIX][RANK][STATE]
        """
        # Clean and format inputs
        site_clean = re.sub(r'[^a-zA-Z]', '', site_name.upper())
        rank_clean = re.sub(r'[^a-zA-Z]', '', rank.upper())
        state_clean = re.sub(r'[^a-zA-Z]', '', state.upper())
        
        # Extract site prefix (first 3 characters)
        site_prefix = site_clean[:3] if len(site_clean) >= 3 else site_clean
        
        # Basic code format
        base_code = f"{site_prefix}{rank_clean}{state_clean}"
        
        # Check if code already exists
        existing_code = self.db.query(WageMaster).filter(
            WageMaster.salary_code == base_code
        ).first()
        
        if not existing_code:
            return base_code
        
        # If code exists, add numeric suffix
        counter = 1
        while True:
            new_code = f"{base_code}{counter:02d}"
            existing = self.db.query(WageMaster).filter(
                WageMaster.salary_code == new_code
            ).first()
            if not existing:
                return new_code
            counter += 1
    
    def create_wage_master(self, wage_data: dict) -> WageMaster:
        """Create new wage master entry"""
        
        # Generate salary code if not provided
        if 'salary_code' not in wage_data or not wage_data['salary_code']:
            wage_data['salary_code'] = self.generate_salary_code(
                wage_data['site_name'],
                wage_data['rank'],
                wage_data['state']
            )
        
        # Check if combination already exists
        existing = self.db.query(WageMaster).filter(
            WageMaster.site_name == wage_data['site_name'],
            WageMaster.rank == wage_data['rank'],
            WageMaster.state == wage_data['state'],
            WageMaster.is_active == True
        ).first()
        
        if existing:
            raise ValueError(f"Wage master already exists for {wage_data['site_name']}-{wage_data['rank']}-{wage_data['state']}")
        
        wage_master = WageMaster(**wage_data)
        self.db.add(wage_master)
        self.db.commit()
        self.db.refresh(wage_master)
        
        return wage_master
    
    def get_all_wage_masters(self, skip: int = 0, limit: int = 100) -> List[WageMaster]:
        """Get all wage masters with pagination"""
        return self.db.query(WageMaster).filter(
            WageMaster.is_active == True
        ).offset(skip).limit(limit).all()
    
    def get_wage_master_by_code(self, salary_code: str) -> Optional[WageMaster]:
        """Get wage master by salary code"""
        return self.db.query(WageMaster).filter(
            WageMaster.salary_code == salary_code,
            WageMaster.is_active == True
        ).first()
    
    def update_wage_master(self, salary_code: str, update_data: dict) -> WageMaster:
        """Update existing wage master"""
        wage_master = self.get_wage_master_by_code(salary_code)
        if not wage_master:
            raise ValueError(f"Wage master with code {salary_code} not found")
        
        for key, value in update_data.items():
            if hasattr(wage_master, key):
                setattr(wage_master, key, value)
        
        self.db.commit()
        self.db.refresh(wage_master)
        return wage_master
    
    def delete_wage_master(self, salary_code: str) -> bool:
        """Soft delete wage master"""
        wage_master = self.get_wage_master_by_code(salary_code)
        if not wage_master:
            raise ValueError(f"Wage master with code {salary_code} not found")
        
        # Check if any employees are using this wage master
        employee_count = self.db.query(Employee).filter(
            Employee.salary_code == salary_code,
            Employee.status == "active"
        ).count()
        
        if employee_count > 0:
            raise ValueError(f"Cannot delete wage master. {employee_count} active employees are using this code.")
        
        wage_master.is_active = False
        self.db.commit()
        return True
    
    def search_wage_masters(self, search_term: str) -> List[WageMaster]:
        """Search wage masters by site name, rank, or state"""
        return self.db.query(WageMaster).filter(
            WageMaster.is_active == True,
            (WageMaster.site_name.ilike(f"%{search_term}%") |
             WageMaster.rank.ilike(f"%{search_term}%") |
             WageMaster.state.ilike(f"%{search_term}%") |
             WageMaster.salary_code.ilike(f"%{search_term}%"))
        ).all()
    
    def get_wage_masters_by_filters(self, filters: dict) -> List[WageMaster]:
        """Get wage masters by specific filters"""
        query = self.db.query(WageMaster).filter(WageMaster.is_active == True)
        
        if filters.get('site_name'):
            query = query.filter(WageMaster.site_name.ilike(f"%{filters['site_name']}%"))
        if filters.get('rank'):
            query = query.filter(WageMaster.rank.ilike(f"%{filters['rank']}%"))
        if filters.get('state'):
            query = query.filter(WageMaster.state.ilike(f"%{filters['state']}%"))
        if filters.get('skill_level'):
            query = query.filter(WageMaster.skill_level == filters['skill_level'])
        
        return query.all()