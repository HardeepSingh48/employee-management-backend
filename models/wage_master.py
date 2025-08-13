from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class WageMaster(Base):
    __tablename__ = "wage_masters"
    
    id = Column(Integer, primary_key=True, index=True)
    salary_code = Column(String(50), unique=True, nullable=False, index=True)
    site_name = Column(String(100), nullable=False)
    rank = Column(String(50), nullable=False)
    state = Column(String(50), nullable=False)
    base_wage = Column(Float, nullable=False)
    skill_level = Column(String(50), nullable=False)  # Highly Skilled, Skilled, Semi-Skilled, Un-Skilled
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String(100))
    
    # Relationship with employees
    employees = relationship("Employee", back_populates="wage_master")
    
    def __repr__(self):
        return f"<WageMaster(salary_code='{self.salary_code}', site='{self.site_name}', rank='{self.rank}')>"

class Employee(Base):
    __tablename__ = "employees"
    
    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(String(50), unique=True, nullable=False, index=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    phone = Column(String(20))
    address = Column(String(500))
    city = Column(String(100))
    state = Column(String(50))
    zip_code = Column(String(20))
    date_of_birth = Column(String(20))
    joining_date = Column(String(20), nullable=False)
    designation = Column(String(100), nullable=False)
    department = Column(String(100), nullable=False)
    reporting_manager = Column(String(100))
    basic_salary = Column(Float, nullable=False)
    allowances = Column(Float, default=0)
    blood_group = Column(String(10))
    emergency_contact = Column(String(100))
    emergency_phone = Column(String(20))
    status = Column(String(20), default="active")
    profile_image = Column(String(500))
    
    # Foreign key to wage master
    salary_code = Column(String(50), ForeignKey("wage_masters.salary_code"))
    wage_master = relationship("WageMaster", back_populates="employees")
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<Employee(employee_id='{self.employee_id}', name='{self.first_name} {self.last_name}')>"
