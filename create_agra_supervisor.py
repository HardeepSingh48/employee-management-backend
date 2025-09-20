import os
from dotenv import load_dotenv

load_dotenv()

from app import create_app
from models import db, User
from models.site import Site
from models.wage_master import WageMaster
import uuid

app = create_app()
app.app_context().push()

def create_agra_metro_supervisor():
    """Create a supervisor specifically for Agra Metro site"""
    
    print("Creating supervisor for Agra Metro site...")
    print("=" * 50)
    
    # First, find the Agra Metro site
    agra_site = Site.query.filter(
        Site.site_name.ilike('%agra%metro%')
    ).first()
    
    if not agra_site:
        # Try to find it in wage masters first
        agra_wage = WageMaster.query.filter(
            WageMaster.site_name.ilike('%agra%metro%')
        ).first()
        
        if agra_wage:
            # Create the site first
            site_id = f"AGRAMETRO-{agra_wage.state.upper()}"
            agra_site = Site(
                site_id=site_id,
                site_name=agra_wage.site_name,
                location=f"{agra_wage.site_name}, {agra_wage.state}",
                state=agra_wage.state,
                is_active=True,
                created_by="admin"
            )
            db.session.add(agra_site)
            db.session.commit()
            print(f"✓ Created site: {site_id} - {agra_wage.site_name}")
        else:
            print("❌ Could not find Agra Metro in wage masters or sites")
            return None
    
    print(f"Using site: {agra_site.site_id} - {agra_site.site_name} ({agra_site.state})")
    
    # Create supervisor for Agra Metro
    supervisor_email = "sup@company.com"
    
    # Check if supervisor already exists
    existing_supervisor = User.query.filter_by(email=supervisor_email).first()
    if existing_supervisor:
        print(f"Supervisor with email {supervisor_email} already exists!")
        print(f"Existing supervisor: {existing_supervisor.name} - {existing_supervisor.role}")
        return existing_supervisor
    
    try:
        supervisor = User(
            id=str(uuid.uuid4()),
            email=supervisor_email,
            name="Rajesh Kumar",  # Indian name for Agra location
            role="supervisor",
            department="Operations",
            site_id=agra_site.site_id,
            created_by="admin@company.com"
        )
        
        supervisor.set_password("sup123")  # Strong password
        supervisor.set_permissions(["read_tasks", "manage_team", "view_reports", "manage_attendance"])
        
        db.session.add(supervisor)
        db.session.commit()
        
        print(f"✓ Created supervisor: {supervisor.email}")
        print(f"  Name: {supervisor.name}")
        print(f"  Site: {agra_site.site_name} ({agra_site.state})")
        print(f"  Department: {supervisor.department}")
        print(f"  Password: AgraSup123!")
        print(f"  Permissions: {supervisor.permissions}")
        
        return supervisor
        
    except Exception as e:
        db.session.rollback()
        print(f"❌ Error creating supervisor: {e}")
        return None

def show_agra_site_info():
    """Show information about Agra Metro site and related data"""
    print("\n" + "=" * 50)
    print("AGRA METRO SITE INFORMATION")
    print("=" * 50)
    
    # Find Agra sites
    agra_sites = Site.query.filter(
        Site.site_name.ilike('%agra%')
    ).all()
    
    if agra_sites:
        for site in agra_sites:
            print(f"Site: {site.site_id}")
            print(f"  Name: {site.site_name}")
            print(f"  Location: {site.location}")
            print(f"  State: {site.state}")
            print(f"  Active: {site.is_active}")
    else:
        print("No Agra sites found in database")
    
    # Find Agra wage masters
    agra_wages = WageMaster.query.filter(
        WageMaster.site_name.ilike('%agra%')
    ).all()
    
    if agra_wages:
        print(f"\nWage Master Records ({len(agra_wages)} found):")
        for wm in agra_wages:
            print(f"  - {wm.salary_code}: {wm.site_name} ({wm.state}) - {wm.rank}")
    
    # Find users for Agra sites
    agra_users = User.query.filter(
        User.site_id.ilike('%agra%')
    ).all()
    
    if agra_users:
        print(f"\nUsers at Agra sites ({len(agra_users)} found):")
        for user in agra_users:
            print(f"  - {user.email}: {user.name} ({user.role})")
    else:
        print("\nNo users found for Agra sites")

if __name__ == "__main__":
    print("Creating supervisor for Agra Metro site...")
    
    # Show current Agra site information
    show_agra_site_info()
    
    # Create the supervisor
    supervisor = create_agra_metro_supervisor()
    
    if supervisor:
        print("\n✅ Agra Metro supervisor created successfully!")
        print(f"\nLogin credentials:")
        print(f"Email: {supervisor.email}")
        print(f"Password: AgraSup123!")
        
        # Show updated information
        show_agra_site_info()
    else:
        print("\n❌ Failed to create Agra Metro supervisor")