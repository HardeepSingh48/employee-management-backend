#!/usr/bin/env python3
"""
Simple test user creation script
Creates basic admin and employee users for testing
"""

from app import create_app
from models import db
from models.user import User
from werkzeug.security import generate_password_hash

def create_simple_test_users():
    """Create basic test users"""
    print("🚀 Creating simple test users")
    print("=" * 50)
    
    app = create_app()
    
    with app.app_context():
        try:
            # Check if users already exist
            admin_user = User.query.filter_by(email="admin@company.com").first()
            employee_user = User.query.filter_by(email="employee@company.com").first()
            
            if admin_user:
                print("✅ Admin user already exists")
            else:
                # Create admin user
                admin_user = User(
                    email="admin@company.com",
                    password_hash=generate_password_hash("admin123"),
                    name="System Administrator",
                    role="admin",
                    is_active=True,
                    is_verified=True
                )
                db.session.add(admin_user)
                print("✅ Created admin user: admin@company.com / admin123")
            
            if employee_user:
                print("✅ Employee user already exists")
            else:
                # Create employee user
                employee_user = User(
                    email="employee@company.com",
                    password_hash=generate_password_hash("emp123"),
                    name="Test Employee",
                    role="employee",
                    is_active=True,
                    is_verified=True
                )
                db.session.add(employee_user)
                print("✅ Created employee user: employee@company.com / emp123")
            
            # Commit changes
            db.session.commit()
            
            # Verify users were created
            total_users = User.query.count()
            print(f"\n📊 Total users in database: {total_users}")
            
            # List all users
            users = User.query.all()
            for user in users:
                print(f"   - {user.email} (role: {user.role}, active: {user.is_active})")
            
            print("\n" + "=" * 50)
            print("🎉 Test users created successfully!")
            print("\n📋 Login credentials:")
            print("Admin: admin@company.com / admin123")
            print("Employee: employee@company.com / emp123")
            print("\n🌐 Test at: http://localhost:3001/login")
            
        except Exception as e:
            print(f"❌ Error creating test users: {str(e)}")
            db.session.rollback()
            return False
    
    return True

if __name__ == "__main__":
    create_simple_test_users()
