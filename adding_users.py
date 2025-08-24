import os

# Set environment variables before importing Flask app
os.environ['DB_USER'] = 'employee_management_db_zwaz_user'
os.environ['DB_PASSWORD'] = 'iJCGc6DAulfzuW758GB3L2yMJOYUPtWY'
os.environ['DB_HOST'] = 'dpg-d2hl5j24d50c739hsm30-a.singapore-postgres.render.com'
os.environ['DB_PORT'] = '5432'
os.environ['DB_NAME'] = 'employee_management_db_zwaz'
os.environ['SECRET_KEY'] = 'd0a5e7a108c0a06668cf1260136e48f8d23d2ef4100a051314f1e1024d498604'

# Alternative: Use full DATABASE_URL (recommended)
os.environ['DATABASE_URL'] = 'postgresql://employee_management_db_zwaz_user:iJCGc6DAulfzuW758GB3L2yMJOYUPtWY@dpg-d2hl5j24d50c739hsm30-a.singapore-postgres.render.com:5432/employee_management_db_zwaz'

from app import create_app  # your Flask app factory
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

def create_employees_and_supervisors():
    """Create employee and supervisor users"""
    
    # Define users to create
    users_to_create = [
        # Employees
        {
            'name': "John Doe",
            'email': "employee@company.com",
            'password': "emp123",
            'role': "employee",
            'department': "Operations",
            'site_id': "SITE-797FE639",  # Update with your valid site_id
            'created_by': "admin@company.com"
        },
        {
            'name': "Sarah Wilson",
            'email': "sarah.wilson@company.com",
            'password': "Employee123!",
            'role': "employee",
            'department': "Operations",
            'site_id': "SITE-797FE639",
            'created_by': "admin@company.com"
        },
        {
            'name': "Mike Johnson",
            'email': "mike.johnson@company.com",
            'password': "Employee123!",
            'role': "employee",
            'department': "Maintenance",
            'site_id': "SITE-797FE639",
            'created_by': "admin@company.com"
        },
        
        # Supervisors
        {
            'name': "Jane Smith",
            'email': "sup@company.com",
            'password': "sup123",
            'role': "supervisor",
            'department': "Operations",
            'site_id': "SITE-797FE639",
            'created_by': "admin@company.com"
        },
        {
            'name': "Robert Brown",
            'email': "robert.brown@company.com",
            'password': "Supervisor123!",
            'role': "supervisor",
            'department': "Maintenance",
            'site_id': "SITE-797FE639",
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
    # Before running, make sure to update the site_id with a valid one from your database
    print("Starting user creation process...")
    print("Note: Make sure to update site_id with a valid value from your database")
    print()
    
    create_employees_and_supervisors()