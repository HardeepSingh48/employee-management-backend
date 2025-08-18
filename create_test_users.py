#!/usr/bin/env python3
"""
Script to create test users for the employee management system
Run this after setting up the database to create admin and employee test accounts
"""

from app import create_app
from models import db
from models.user import User
from models.employee import Employee
from models.department import Department
from models.wage_master import WageMaster

def create_test_users():
    """Create test users for the system"""
    app = create_app()
    
    with app.app_context():
        print("🚀 Creating test users for Employee Management System")
        print("=" * 60)
        
        # Create tables if they don't exist
        db.create_all()
        
        # Create test department
        dept = Department.query.filter_by(department_id="IT").first()
        if not dept:
            dept = Department(
                department_id="IT",
                department_name="Information Technology",
                description="IT Department",
                created_by="system"
            )
            db.session.add(dept)
            print("✅ Created IT Department")
        
        # Create test salary code
        wage_master = WageMaster.query.filter_by(salary_code="TEST-ADMIN-MH").first()
        if not wage_master:
            wage_master = WageMaster(
                salary_code="TEST-ADMIN-MH",
                site_name="Test Site",
                rank="Admin",
                state="Maharashtra",
                base_wage=1000.0,
                skill_level="Highly Skilled",
                created_by="system"
            )
            db.session.add(wage_master)
            print("✅ Created test salary code: TEST-ADMIN-MH")
        
        # Create test employee record
        employee = Employee.query.filter_by(employee_id="EMP001").first()
        if not employee:
            employee = Employee(
                employee_id="EMP001",
                first_name="John",
                last_name="Doe",
                email="employee@company.com",
                phone_number="9876543210",
                address="123 Test Street, Mumbai",
                department_id="IT",
                designation="Software Developer",
                salary_code="TEST-ADMIN-MH",
                employment_status="Active",
                gender="Male",
                marital_status="Single",
                created_by="system"
            )
            db.session.add(employee)
            print("✅ Created test employee: EMP001 - John Doe")
        
        # Create admin user
        admin_user = User.query.filter_by(email="admin@company.com").first()
        if not admin_user:
            admin_user = User(
                email="admin@company.com",
                name="System Administrator",
                role="admin",
                department="IT",
                created_by="system"
            )
            admin_user.set_password("admin123")
            admin_user.set_permissions(['all'])
            db.session.add(admin_user)
            print("✅ Created admin user: admin@company.com / admin123")
        
        # Create employee user
        employee_user = User.query.filter_by(email="employee@company.com").first()
        if not employee_user:
            employee_user = User(
                email="employee@company.com",
                name="John Doe",
                role="employee",
                employee_id="EMP001",
                department="IT",
                created_by="system"
            )
            employee_user.set_password("emp123")
            employee_user.set_permissions(['view_profile', 'mark_attendance', 'view_attendance'])
            db.session.add(employee_user)
            print("✅ Created employee user: employee@company.com / emp123")
        
        # Commit all changes
        db.session.commit()
        
        print("\n" + "=" * 60)
        print("🎉 Test users created successfully!")
        print("\n📋 Login Credentials:")
        print("-" * 30)
        print("👨‍💼 Admin Login:")
        print("   Email: admin@company.com")
        print("   Password: admin123")
        print("   Role: Admin")
        print("\n👨‍💻 Employee Login:")
        print("   Email: employee@company.com")
        print("   Password: emp123")
        print("   Role: Employee")
        print("   Employee ID: EMP001")
        
        print("\n🔗 Access URLs:")
        print("-" * 30)
        print("   Frontend: http://localhost:3000")
        print("   Backend API: http://localhost:5000")
        print("   Login Page: http://localhost:3000/login")
        
        print("\n✨ You can now test the complete employee management system!")
        print("   - Admin can manage employees, salary codes, attendance, and salary calculations")
        print("   - Employee can mark attendance, view profile, and check salary information")

if __name__ == "__main__":
    create_test_users()
