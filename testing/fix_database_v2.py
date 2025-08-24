from app import create_app
from models import db
from sqlalchemy import text

app = create_app(register_blueprints=False)

with app.app_context():
    try:
        # First, create the sites table
        print("Creating sites table...")
        with db.engine.connect() as connection:
            connection.execute(text('''
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
            '''))
            connection.commit()
        print("✅ Sites table created/verified")
        
    except Exception as e:
        print(f"Sites table error: {e}")
    
    try:
        # Add site_id column to users table
        print("Adding site_id to users table...")
        with db.engine.connect() as connection:
            connection.execute(text('ALTER TABLE users ADD COLUMN site_id VARCHAR(50)'))
            connection.commit()
        print("✅ Added site_id column to users table")
        
    except Exception as e:
        print(f"Users site_id column (might already exist): {e}")
        
    try:
        # Add site_id column to employees table
        print("Adding site_id to employees table...")
        with db.engine.connect() as connection:
            connection.execute(text('ALTER TABLE employees ADD COLUMN site_id VARCHAR(50)'))
            connection.commit()
        print("✅ Added site_id column to employees table")
        
    except Exception as e:
        print(f"Employees site_id column (might already exist): {e}")
    
    try:
        # Add foreign key constraints (optional - might fail on managed databases)
        print("Adding foreign key constraints...")
        with db.engine.connect() as connection:
            connection.execute(text('''
                ALTER TABLE users 
                ADD CONSTRAINT fk_users_site_id 
                FOREIGN KEY (site_id) REFERENCES sites(site_id)
            '''))
            connection.commit()
        print("✅ Added users foreign key constraint")
        
    except Exception as e:
        print(f"Users FK constraint (this is optional): {e}")
        
    try:
        with db.engine.connect() as connection:
            connection.execute(text('''
                ALTER TABLE employees 
                ADD CONSTRAINT fk_employees_site_id 
                FOREIGN KEY (site_id) REFERENCES sites(site_id)
            '''))
            connection.commit()
        print("✅ Added employees foreign key constraint")
        
    except Exception as e:
        print(f"Employees FK constraint (this is optional): {e}")
    
    print("\n🎉 Database schema update completed!")
    
    # Now test if we can query users without the site_id error
    try:
        from models.user import User
        user_count = User.query.count()
        print(f"✅ Can now query users successfully! Found {user_count} users.")
    except Exception as e:
        print(f"❌ Still having issues with User model: {e}")