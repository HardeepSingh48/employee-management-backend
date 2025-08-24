from app import create_app
from models import db

app = create_app(register_blueprints=False)

with app.app_context():
    try:
        # Add name column to users table
        db.engine.execute('ALTER TABLE users ADD COLUMN name VARCHAR(200)')
        print("✅ Added 'name' column to users table")
        
        # Update existing users with a default name based on email
        db.engine.execute('''
            UPDATE users 
            SET name = COALESCE(
                SPLIT_PART(email, '@', 1), 
                'User'
            ) 
            WHERE name IS NULL OR name = ''
        ''')
        print("✅ Updated existing users with default names")
        
    except Exception as e:
        print(f"Error: {e}")
        # Try alternative syntax for different databases
        try:
            db.engine.execute('ALTER TABLE users ADD name VARCHAR(200)')
            print("✅ Added 'name' column (alternative method)")
            
            # Update with simpler method
            db.engine.execute("UPDATE users SET name = 'User' WHERE name IS NULL")
            print("✅ Updated users with default name")
            
        except Exception as e2:
            print(f"Still failed: {e2}")