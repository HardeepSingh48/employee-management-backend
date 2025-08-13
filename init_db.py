#!/usr/bin/env python3
"""
Database initialization script for Employee Management System
"""

import os
import sys
from flask import Flask
from models import db
from config import SQLALCHEMY_DATABASE_URI, SQLALCHEMY_TRACK_MODIFICATIONS, SECRET_KEY

def init_database():
    """Initialize the database with all tables"""

    # Create Flask app for database initialization
    app = Flask(__name__)

    # Check if we should use admin credentials for initialization
    admin_user = os.getenv("ADMIN_DB_USER", "postgres")
    admin_password = os.getenv("ADMIN_DB_PASSWORD", "password")
    db_host = os.getenv("DB_HOST", "localhost")
    db_port = os.getenv("DB_PORT", "5432")
    db_name = os.getenv("DB_NAME", "sspl_db")

    # Use admin credentials if provided, otherwise use regular config
    if os.getenv("USE_ADMIN_CREDS", "false").lower() == "true":
        admin_uri = f"postgresql://{admin_user}:{admin_password}@{db_host}:{db_port}/{db_name}"
        app.config["SQLALCHEMY_DATABASE_URI"] = admin_uri
        print(f"Using admin credentials for database initialization...")
    else:
        app.config["SQLALCHEMY_DATABASE_URI"] = SQLALCHEMY_DATABASE_URI
        print(f"Using regular credentials for database initialization...")

    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = SQLALCHEMY_TRACK_MODIFICATIONS
    app.config["SECRET_KEY"] = SECRET_KEY

    db.init_app(app)
    
    with app.app_context():
        print("Creating database tables...")
        
        # Create all tables
        db.create_all()
        
        print("✅ Database tables created successfully!")
        
        # Create some sample departments
        from models.department import Department
        
        # Check if departments already exist
        existing_dept = Department.query.first()
        if not existing_dept:
            print("Creating sample departments...")
            
            departments = [
                {"department_id": "IT", "department_name": "Information Technology", "description": "IT Department"},
                {"department_id": "HR", "department_name": "Human Resources", "description": "HR Department"},
                {"department_id": "FIN", "department_name": "Finance", "description": "Finance Department"},
                {"department_id": "OPS", "department_name": "Operations", "description": "Operations Department"},
            ]
            
            for dept_data in departments:
                dept = Department(
                    department_id=dept_data["department_id"],
                    department_name=dept_data["department_name"],
                    description=dept_data["description"],
                    created_by="system"
                )
                db.session.add(dept)
            
            db.session.commit()
            print("✅ Sample departments created!")
        
        # Create some sample wage masters
        from models.wage_master import WageMaster
        
        existing_wage = WageMaster.query.first()
        if not existing_wage:
            print("Creating sample wage masters...")
            
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
            
            db.session.commit()
            print("✅ Sample wage masters created!")
        
        print("\n🎉 Database initialization completed successfully!")
        print("\nYou can now:")
        print("1. Register employees using: POST http://127.0.0.1:5000/api/employees/register")
        print("2. View departments using: GET http://127.0.0.1:5000/api/departments/")
        print("3. List employees using: GET http://127.0.0.1:5000/api/employees/")

if __name__ == "__main__":
    try:
        init_database()
    except Exception as e:
        print(f"❌ Error initializing database: {e}")
        sys.exit(1)
