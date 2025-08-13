#!/usr/bin/env python3
"""
Completely recreate the database - drops all tables and recreates them
"""

import os
import sys
from flask import Flask
from models import db
from models.department import Department
from models.wage_master import WageMaster
from config import SQLALCHEMY_DATABASE_URI, SQLALCHEMY_TRACK_MODIFICATIONS, SECRET_KEY

def recreate_database():
    """Drop all tables and recreate them with sample data"""
    
    # Create Flask app for database operations
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = SQLALCHEMY_DATABASE_URI
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = SQLALCHEMY_TRACK_MODIFICATIONS
    app.config["SECRET_KEY"] = SECRET_KEY
    
    db.init_app(app)
    
    with app.app_context():
        try:
            print("🗑️  Dropping all existing tables...")
            db.drop_all()
            print("✅ All tables dropped!")
            
            print("🏗️  Creating all tables...")
            db.create_all()
            print("✅ All tables created!")
            
            # Create departments (matching frontend options)
            print("📁 Creating departments...")
            departments = [
                {"department_id": "HR", "department_name": "Human Resources", "description": "HR Department"},
                {"department_id": "IT", "department_name": "Information Technology", "description": "IT Department"},
                {"department_id": "FIN", "department_name": "Finance", "description": "Finance Department"},
                {"department_id": "MKT", "department_name": "Marketing", "description": "Marketing Department"},
                {"department_id": "OPS", "department_name": "Operations", "description": "Operations Department"},
                {"department_id": "SAL", "department_name": "Sales", "description": "Sales Department"},
                {"department_id": "ENG", "department_name": "Engineering", "description": "Engineering Department"},
                {"department_id": "CS", "department_name": "Customer Support", "description": "Customer Support Department"},
                {"department_id": "LEG", "department_name": "Legal", "description": "Legal Department"},
                {"department_id": "ADM", "department_name": "Administration", "description": "Administration Department"},
            ]
            
            for dept_data in departments:
                dept = Department(
                    department_id=dept_data["department_id"],
                    department_name=dept_data["department_name"],
                    description=dept_data["description"],
                    created_by="system"
                )
                db.session.add(dept)
            
            print(f"✅ Created {len(departments)} departments!")
            
            # Create sample wage masters/salary codes
            print("💰 Creating sample salary codes...")
            wage_masters = [
                {
                    "salary_code": "DELENGINEERDELHI",
                    "site_name": "Delhi Central",
                    "rank": "Engineer",
                    "state": "Delhi",
                    "base_wage": 50000,
                    "skill_level": "Skilled"
                },
                {
                    "salary_code": "DELSUPERVISORDELHI",
                    "site_name": "Delhi Central", 
                    "rank": "Supervisor",
                    "state": "Delhi",
                    "base_wage": 60000,
                    "skill_level": "Highly Skilled"
                },
                {
                    "salary_code": "MUMMANAGERMAH",
                    "site_name": "Mumbai Office",
                    "rank": "Manager", 
                    "state": "Maharashtra",
                    "base_wage": 80000,
                    "skill_level": "Highly Skilled"
                },
                {
                    "salary_code": "BLRDEVKARN",
                    "site_name": "Bangalore Tech",
                    "rank": "Developer", 
                    "state": "Karnataka",
                    "base_wage": 55000,
                    "skill_level": "Skilled"
                },
                {
                    "salary_code": "CHNSUPPORTTN",
                    "site_name": "Chennai Support",
                    "rank": "Support", 
                    "state": "Tamil Nadu",
                    "base_wage": 35000,
                    "skill_level": "Semi-Skilled"
                }
            ]
            
            for wage_data in wage_masters:
                wage = WageMaster(
                    salary_code=wage_data["salary_code"],
                    site_name=wage_data["site_name"],
                    rank=wage_data["rank"],
                    state=wage_data["state"],
                    base_wage=wage_data["base_wage"],
                    skill_level=wage_data["skill_level"],
                    created_by="system"
                )
                db.session.add(wage)
            
            print(f"✅ Created {len(wage_masters)} salary codes!")
            
            # Commit all changes
            db.session.commit()
            
            print("\n🎉 Database recreated successfully!")
            print("\n📊 Summary:")
            print(f"   • {len(departments)} departments created")
            print(f"   • {len(wage_masters)} salary codes created")
            print("   • All tables recreated with proper constraints")
            
            print("\n🚀 You can now:")
            print("1. Start the backend server: python app.py")
            print("2. Register employees using the frontend form")
            print("3. View departments: GET http://127.0.0.1:5000/api/departments/")
            print("4. View salary codes: GET http://127.0.0.1:5000/api/salary-codes/")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error recreating database: {e}")
            sys.exit(1)

if __name__ == "__main__":
    recreate_database()
