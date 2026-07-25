import os
import uuid
from datetime import date
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from app import create_app
from models import db
from models.user import User
from models.employee import Employee
from models.department import Department
from models.site import Site
from sqlalchemy import text

# Initialize app context
app = create_app()
app.app_context().push()

def inject_employee():
    print("Starting injection of test employee...")
    
    # 1. Ensure Department "IT" exists
    dept = Department.query.filter_by(department_id="IT").first()
    if not dept:
        dept = Department(
            department_id="IT",
            department_name="Information Technology",
            description="IT Department",
            is_active=True,
            created_by="injector"
        )
        db.session.add(dept)
        db.session.flush()
        print("Created Department: IT")
    else:
        print("Found existing Department: IT")

    # 2. Try to find a usable salary code and site name from wage_masters using raw SQL
    # This avoids ORM query on WageMaster which fails due to missing site_id column
    wage_row = db.session.execute(text("SELECT salary_code, site_name FROM wage_masters LIMIT 1")).fetchone()
    
    if wage_row:
        salary_code = wage_row[0]
        site_name = wage_row[1]
        print(f"Found existing salary code '{salary_code}' for site '{site_name}' in database.")
        
        # Check if site exists in database
        site = Site.query.filter_by(site_name=site_name).first()
        if not site:
            site_id = f"SITE-{uuid.uuid4().hex[:8].upper()}"
            site = Site(
                site_id=site_id,
                site_name=site_name,
                location="28.6139, 77.2090",
                state="Delhi",
                is_active=True,
                created_by="injector"
            )
            db.session.add(site)
            db.session.flush()
            print(f"Created Site record '{site_name}' with ID '{site_id}' to link with wage master.")
        else:
            print(f"Found matching Site: {site.site_name} (ID: {site.site_id})")
    else:
        # Create a new test site and insert a matching wage master row via raw SQL
        site_name = "Test Site"
        site = Site.query.filter_by(site_name=site_name).first()
        if not site:
            site_id = f"SITE-{uuid.uuid4().hex[:8].upper()}"
            site = Site(
                site_id=site_id,
                site_name=site_name,
                location="28.6139, 77.2090",
                state="Delhi",
                is_active=True,
                created_by="injector"
            )
            db.session.add(site)
            db.session.flush()
            print(f"Created Site: {site.site_name} (ID: {site.site_id})")
        else:
            print(f"Found existing Site: {site.site_name} (ID: {site.site_id})")
            
        salary_code = "SC-TEST"
        # Check if salary code exists using raw SQL
        existing_wage = db.session.execute(
            text("SELECT salary_code FROM wage_masters WHERE salary_code = :code"), 
            {"code": salary_code}
        ).fetchone()
        
        if not existing_wage:
            db.session.execute(
                text(
                    "INSERT INTO wage_masters (salary_code, site_name, rank, state, base_wage, skill_level, is_active, created_by) "
                    "VALUES (:code, :site_name, 'Associate', 'Delhi', 500.0, 'Skilled', true, 'injector')"
                ),
                {"code": salary_code, "site_name": site_name}
            )
            print("Created WageMaster entry using raw SQL: SC-TEST")
        else:
            print("Found existing WageMaster: SC-TEST")

    # 3. Create Employee
    email = "akemployee@ssplsecurity.com"
    username = "akemployee"
    password = "password123"
    
    emp = Employee.query.filter_by(email=email).first()
    if emp:
        print(f"Employee with email {email} already exists (ID: {emp.employee_id}).")
        # Ensure user account exists
        user = User.query.filter_by(employee_id=emp.employee_id).first()
        if not user:
            user = User(
                id=str(uuid.uuid4()),
                email=email,
                username=username,
                name="Abhishek Employee",
                role="employee",
                employee_id=emp.employee_id,
                created_by="injector"
            )
            user.set_password(password)
            user.set_permissions(["view_profile", "mark_attendance", "view_attendance"])
            db.session.add(user)
            db.session.commit()
            print(f"Created user account for existing employee. Login: {email} / {password}")
        else:
            user.set_password(password)
            db.session.commit()
            print(f"User account already exists. Password has been reset to '{password}'.")
        return

    # Let the database generate the employee_id from sequence
    emp = Employee(
        first_name="Abhishek",
        last_name="Employee",
        email=email,
        phone_number="9876543210",
        department_id=dept.department_id,
        designation="Software Engineer",
        employment_status="Active",
        salary_code=salary_code,
        site_id=site.site_id,
        created_by="injector",
        date_of_birth=date(1995, 8, 15),
        hire_date=date.today()
    )
    db.session.add(emp)
    db.session.flush()  # Generate employee_id

    # 4. Create associated User account
    user = User(
        id=str(uuid.uuid4()),
        email=email,
        username=username,
        name="Abhishek Employee",
        role="employee",
        employee_id=emp.employee_id,
        created_by="injector"
    )
    user.set_password(password)
    user.set_permissions(["view_profile", "mark_attendance", "view_attendance"])
    
    if hasattr(user, 'is_temp_password'):
        user.is_temp_password = False

    db.session.add(user)
    db.session.commit()

    print("\n==========================================")
    print("SUCCESS: Test Employee Injected Successfully!")
    print("==========================================")
    print(f"Employee ID:  {emp.employee_id}")
    print(f"Name:         {emp.first_name} {emp.last_name}")
    print(f"Designation:  {emp.designation}")
    print(f"Department:   {emp.department_id}")
    print(f"Site Name:    {site.site_name} (ID: {site.site_id})")
    print(f"Salary Code:  {emp.salary_code}")
    print("------------------------------------------")
    print("Login Credentials for App testing:")
    print(f"Identifier:   {email}  (or: {username})")
    print(f"Password:     {password}")
    print("==========================================\n")

if __name__ == "__main__":
    inject_employee()
