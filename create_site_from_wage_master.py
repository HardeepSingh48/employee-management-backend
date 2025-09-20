# create_site_from_wage_master.py
import os
from dotenv import load_dotenv

load_dotenv()

from app import create_app
from models import db
from models.wage_master import WageMaster
from models.site import Site

app = create_app()
app.app_context().push()

def create_sites_from_wage_masters():
    """Create sites based on existing wage master data"""
    
    print("Looking for wage master data to create sites...")
    
    # Get unique combinations of site info from wage masters
    wage_masters = WageMaster.query.all()
    
    if not wage_masters:
        print("No wage master data found!")
        return
    
    sites_created = 0
    created_sites = set()  # Track created sites to avoid duplicates
    
    for wm in wage_masters:
        # Create site_id based on site_name and state
        site_name_clean = wm.site_name.replace(' ', '').upper()
        state_clean = wm.state.upper()
        site_id = f"{site_name_clean}-{state_clean}"
        
        # Skip if we already created this site
        if site_id in created_sites:
            continue
            
        # Check if site already exists in database
        existing_site = Site.query.filter_by(site_id=site_id).first()
        
        if not existing_site:
            try:
                new_site = Site(
                    site_id=site_id,
                    site_name=wm.site_name,
                    location=f"{wm.site_name}, {wm.state}",
                    state=wm.state,
                    is_active=True,
                    created_by="system"
                )
                
                db.session.add(new_site)
                db.session.commit()
                
                print(f"✓ Created site: {site_id} - {wm.site_name} ({wm.state})")
                sites_created += 1
                created_sites.add(site_id)
                
            except Exception as e:
                print(f"✗ Error creating site {site_id}: {e}")
                db.session.rollback()
        else:
            print(f"⚠ Site {site_id} already exists, skipping")
            created_sites.add(site_id)
    
    print(f"\n✅ Created {sites_created} new sites from wage master data")
    
    # Show all sites
    all_sites = Site.query.all()
    print(f"\nAll sites in database ({len(all_sites)} total):")
    for site in all_sites:
        print(f"  - {site.site_id}: {site.site_name} ({site.state})")
    
    return len(all_sites) > 0

if __name__ == "__main__":
    print("Creating sites from wage master data...")
    print("=" * 50)
    
    success = create_sites_from_wage_masters()
    
    if success:
        print("\n✅ Sites created successfully!")
        print("You can now run your user creation script.")
    else:
        print("\n❌ No sites could be created from wage master data.")
        print("You may need to manually add site data first.")