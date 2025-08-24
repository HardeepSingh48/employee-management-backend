from app import create_app
from models import db

app = create_app(register_blueprints=False)

with app.app_context():
    try:
        # First, create the sites table
        print("Creating sites table...")
        db.engine.execute('''
            CREATE TABLE IF NOT EXISTS sites (
                site_id VARCHAR(50) PRIMARY KEY,
                site_name VARCHAR(200) NOT NULL,
                location VARCHAR(500),
                state VARCHAR(100),
                is_active BOOLEAN DEFAULT TRUE,
                created_date DATE DEFAULT CURRENT_DATE,
                created_by VARCHAR(100),
                updated_date DATE,
                updated_by VARCHAR(100)
            )
        ''')
        print("✅ Sites table created/verified")
        
    except Exception as e:
        print(f"Sites table error: {e}")
    
    try:
        # Add site_id column to users table
        print("Adding site_id to users table...")
        db.engine.execute('ALTER TABLE users ADD COLUMN site_id VARCHAR(50)')
        print("✅ Added site_id column to users table")
        
    except Exception as e:
        print(f"Users site_id column: {e}")
        
    try:
        # Add site_id column to employees table
        print("Adding site_id to employees table...")
        db.engine.execute('ALTER TABLE employees ADD COLUMN site_id VARCHAR(50)')
        print("✅ Added site_id column to employees table")
        
    except Exception as e:
        print(f"Employees site_id column: {e}")
    
    try:
        # Add foreign key constraints
        print("Adding foreign key constraints...")
        db.engine.execute('''
            ALTER TABLE users 
            ADD CONSTRAINT fk_users_site_id 
            FOREIGN KEY (site_id) REFERENCES sites(site_id)
        ''')
        print("✅ Added users foreign key constraint")
        
    except Exception as e:
        print(f"Users FK constraint: {e}")
        
    try:
        db.engine.execute('''
            ALTER TABLE employees 
            ADD CONSTRAINT fk_employees_site_id 
            FOREIGN KEY (site_id) REFERENCES sites(site_id)
        ''')
        print("✅ Added employees foreign key constraint")
        
    except Exception as e:
        print(f"Employees FK constraint: {e}")
    
    print("\n🎉 Database schema update completed!")
    print("You can now test the login and other features.")