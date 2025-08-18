#!/usr/bin/env python3
"""
Database initialization script
Creates all database tables and optionally creates test users
"""

from app import create_app
from models import db
from models.user import User
from models.employee import Employee
from models.department import Department
from models.wage_master import WageMaster

def init_database():
    """Initialize the database with all tables"""
    print("🚀 Initializing Employee Management System Database")
    print("=" * 60)
    
    app = create_app()
    
    with app.app_context():
        try:
            # Drop all tables (optional - uncomment if you want to reset)
            # print("Dropping existing tables...")
            # db.drop_all()
            
            # Create all tables
            print("Creating database tables...")
            db.create_all()
            
            # Verify tables were created
            inspector = db.inspect(db.engine)
            tables = inspector.get_table_names()
            
            print(f"✅ Successfully created {len(tables)} tables:")
            for table in sorted(tables):
                print(f"   - {table}")
            
            print("\n" + "=" * 60)
            print("🎉 Database initialization completed successfully!")
            print("\n📋 Next steps:")
            print("1. Run: python create_test_users.py (to create test users)")
            print("2. Start the server: python app.py")
            print("3. Test login at: http://localhost:3001/login")
            
        except Exception as e:
            print(f"❌ Error initializing database: {str(e)}")
            print("\n🔧 Troubleshooting:")
            print("1. Check your database connection in config.py")
            print("2. Ensure PostgreSQL is running")
            print("3. Verify database credentials")
            return False
    
    return True

if __name__ == "__main__":
    init_database()
