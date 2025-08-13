#!/usr/bin/env python3
"""
Add missing departments to match frontend options
"""

import os
import sys
from flask import Flask
from models import db
from models.department import Department
from config import SQLALCHEMY_DATABASE_URI, SQLALCHEMY_TRACK_MODIFICATIONS, SECRET_KEY

def add_missing_departments():
    """Add missing departments to match frontend options"""
    
    # Create Flask app for database operations
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = SQLALCHEMY_DATABASE_URI
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = SQLALCHEMY_TRACK_MODIFICATIONS
    app.config["SECRET_KEY"] = SECRET_KEY
    
    db.init_app(app)
    
    with app.app_context():
        try:
            print("Adding missing departments...")
            
            # Define all departments that should exist (matching frontend)
            all_departments = [
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
            
            # Check which departments already exist
            existing_departments = {dept.department_id for dept in Department.query.all()}
            print(f"Existing departments: {existing_departments}")
            
            # Add missing departments
            added_count = 0
            for dept_data in all_departments:
                if dept_data["department_id"] not in existing_departments:
                    dept = Department(
                        department_id=dept_data["department_id"],
                        department_name=dept_data["department_name"],
                        description=dept_data["description"],
                        created_by="system"
                    )
                    db.session.add(dept)
                    added_count += 1
                    print(f"Added: {dept_data['department_id']} - {dept_data['department_name']}")
            
            if added_count > 0:
                db.session.commit()
                print(f"✅ Added {added_count} missing departments!")
            else:
                print("✅ All departments already exist!")
            
            # Show all departments
            all_depts = Department.query.all()
            print("\nAll departments in database:")
            for dept in all_depts:
                print(f"  {dept.department_id}: {dept.department_name}")
                
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error adding departments: {e}")
            sys.exit(1)

if __name__ == "__main__":
    add_missing_departments()
