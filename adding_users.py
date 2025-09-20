import os
from dotenv import load_dotenv

# Load environment variables from .env file (Supabase config)
load_dotenv()

# Verify we're using the correct database
print("=== Database Configuration ===")
print(f"DB_HOST: {os.getenv('DB_HOST')}")
print(f"DB_USER: {os.getenv('DB_USER')}")
print(f"DB_NAME: {os.getenv('DB_NAME')}")
print("=" * 50)

from app import create_app
from models import db, User
import uuid

# Initialize app context
app = create_app()
app.app_context().push()

def add_user(email, password, role, name, department=None, site_id=None, created_by=None):
    """Helper function to create a user safely"""
    role = role.strip().lower() 
    
    # Check if user with this email already exists
    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        print(f"User with email {email} already exists. Skipping creation.")
        return existing_user

    # Validate role - only allow employee and supervisor
    if role not in ['employee', 'supervisor']:
        print(f"Invalid role: {role}. Only 'employee' and 'supervisor' roles are allowed.")
        return None

    # Basic password validation
    if len(password) < 6:
        print(f"Password too weak for {email}. Must be at least 6 characters.")
        return None

    try:
        user = User(
            id=str(uuid.uuid4()),
            email=email,
            name=name,
            role=role,
            department=department,
            site_id=site_id,
            created_by=created_by
        )
        user.set_password(password)
        
        # Set default permissions based on role
        if role == "employee":
            user.set_permissions(["read_tasks"])
        elif role == "supervisor":
            user.set_permissions(["read_tasks", "manage_team"])

        db.session.add(user)
        db.session.commit()
        print(f"✓ Created {role}: {email} (ID: {user.id})")
        return user
        
    except Exception as e:
        db.session.rollback()
        print(f"✗ Error creating user {email}: {str(e)}")
        return None

def get_valid_site_id():
    """Get a valid site_id from the database"""
    try:
        from models.site import Site
        site = Site.query.first()
        if site:
            print(f"Using site_id: {site.site_id}")
            return site.site_id
        else:
            print("No sites found in database. Creating a default site...")
            # Create a default site with required state field
            default_site = Site(
                site_id="DEFAULT-SITE-001",
                site_name="Default Site",
                location="Main Office",
                state="Delhi",  # Required field
                is_active=True,
                created_by="system"
            )
            db.session.add(default_site)
            db.session.commit()
            print(f"Created default site: {default_site.site_id}")
            return default_site.site_id
    except Exception as e:
        print(f"Error getting site_id: {e}")
        db.session.rollback()  # Rollback the failed transaction
        return "DEFAULT-SITE-001"  # fallback

def create_employees_and_supervisors():
    """Create employee and supervisor users"""
    
    # Get a valid site_id from the database
    valid_site_id = get_valid_site_id()
    
    # Define users to create
    users_to_create = [
        # Employees
        {
            'name': "John Doe",
            'email': "employee@company.com",
            'password': "emp123",
            'role': "employee",
            'department': "Operations",
            'site_id': valid_site_id,
            'created_by': "admin@company.com"
        },
        {
            'name': "Sarah Wilson",
            'email': "sarah.wilson@company.com",
            'password': "Employee123!",
            'role': "employee",
            'department': "Operations",
            'site_id': valid_site_id,
            'created_by': "admin@company.com"
        },
        {
            'name': "Mike Johnson",
            'email': "mike.johnson@company.com",
            'password': "Employee123!",
            'role': "employee",
            'department': "Maintenance",
            'site_id': valid_site_id,
            'created_by': "admin@company.com"
        },
        
        # Supervisors
        {
            'name': "Jane Smith",
            'email': "sup@company.com",
            'password': "sup123",
            'role': "supervisor",
            'department': "Operations",
            'site_id': valid_site_id,
            'created_by': "admin@company.com"
        },
        {
            'name': "Robert Brown",
            'email': "robert.brown@company.com",
            'password': "Supervisor123!",
            'role': "supervisor",
            'department': "Maintenance",
            'site_id': valid_site_id,
            'created_by': "admin@company.com"
        }
    ]

    print("Creating employees and supervisors...")
    print("=" * 50)
    
    created_users = []
    employees_count = 0
    supervisors_count = 0
    
    for user_data in users_to_create:
        user = add_user(**user_data)
        if user:
            created_users.append(user)
            if user.role == 'employee':
                employees_count += 1
            elif user.role == 'supervisor':
                supervisors_count += 1
    
    print("=" * 50)
    print(f"Summary:")
    print(f"✓ Created {employees_count} employees")
    print(f"✓ Created {supervisors_count} supervisors")
    print(f"✓ Total users created: {len(created_users)}")
    
    return created_users

if __name__ == "__main__":
    print("Starting user creation process...")
    print("Using Supabase database configuration from .env file")
    print()
    
    # Test database connection first
    try:
        from models.user import User
        user_count = User.query.count()
        print(f"✓ Database connection successful! Current users: {user_count}")
        print()
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        print("Please check your .env file and database configuration.")
        exit(1)
    
    create_employees_and_supervisors()